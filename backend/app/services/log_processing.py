"""Background log processing: parse -> template mining -> bulk insert, with progress and retry safety."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.log import LogUpload
from app.parsers.drain_parser import create_extractor
from app.parsers.log_parser import LogParseError, ParseStats, iter_records, update_stats
from app.parsers.regex_parser import ParserConfig
from app.repositories.audit_repository import AuditRepository
from app.repositories.log_repository import LogRepository

logger = logging.getLogger(__name__)


class LogProcessor:
    """Runs outside the request cycle with its own DB session.

    Two passes over the stored file (never fully in memory):
      1. parse every line, gather statistics, let the template miner learn;
      2. parse again and insert rows using the converged templates.
    A PENDING -> PROCESSING compare-and-set prevents two workers processing the same upload.
    """

    def __init__(self, session_factory: Callable[[], Session], settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    def process(self, upload_id: int) -> None:
        with self.session_factory() as db:
            repo = LogRepository(db)
            if not repo.claim_for_processing(upload_id, datetime.now(UTC)):
                logger.info("Upload %s was not claimable (already processing or finished)", upload_id)
                return
            try:
                self._run(db, repo, upload_id)
            except LogParseError as exc:
                self._fail(db, upload_id, str(exc))
            except Exception as exc:
                logger.exception("Processing failed for upload %s", upload_id)
                self._fail(db, upload_id, f"Processing failed ({type(exc).__name__}). You can retry.")

    def _fail(self, db: Session, upload_id: int, message: str) -> None:
        db.rollback()
        upload = db.get(LogUpload, upload_id)
        if upload is None:
            return
        upload.status = "FAILED"
        upload.error_message = message[:500]
        upload.completed_at = datetime.now(UTC)
        AuditRepository(db).record("log.processing_failed", upload.user_id, None, "log_upload", str(upload_id))
        db.commit()

    def _run(self, db: Session, repo: LogRepository, upload_id: int) -> None:
        upload = db.get(LogUpload, upload_id)
        assert upload is not None
        path = Path(self.settings.upload_dir) / upload.stored_path
        user_id = upload.user_id
        config = ParserConfig(
            extra_patterns=self.settings.log_extra_patterns_list, default_year=upload.created_at.year
        )
        max_len = self.settings.log_max_line_length
        extractor = create_extractor(self.settings.log_template_miner)
        stats = ParseStats(parser_used=extractor.name)

        # Pass 1: statistics + template learning
        for record in iter_records(path, config, max_len):
            update_stats(stats, record)
            if record.message.strip():
                extractor.learn(record.message)
        if stats.entries == 0:
            raise LogParseError("No log lines were found in the file")
        upload.total_lines = stats.total_lines
        db.commit()

        # Pass 2: insert rows (idempotent: previous partial results are removed first)
        repo.delete_entries(upload_id)
        db.commit()
        template_ids: dict[str, int] = {}
        batch: list[dict[str, Any]] = []
        inserted = 0
        for record in iter_records(path, config, max_len):
            if not record.message.strip() and not record.raw.strip():
                continue
            result = extractor.extract(record.message or record.raw)
            if result.template_hash not in template_ids:
                template_ids[result.template_hash] = repo.get_or_create_template(
                    user_id, result.template_hash, result.template_text
                )
            batch.append(
                {
                    "upload_id": upload_id,
                    "user_id": user_id,
                    "line_number": record.line_number,
                    "timestamp": record.timestamp,
                    "level": record.level,
                    "service": record.service[:128],
                    "hostname": record.hostname[:255],
                    "message": record.message or record.raw,
                    "original_message": record.raw,
                    "template_id": template_ids[result.template_hash],
                    "parameters": result.parameters,
                    "truncated": record.truncated,
                }
            )
            if len(batch) >= self.settings.log_batch_size:
                inserted += self._flush(db, repo, upload_id, batch, inserted)
                batch = []
        inserted += self._flush(db, repo, upload_id, batch, inserted)

        stats.template_count = len(template_ids)
        stats.extractor_errors = extractor.errors
        upload.parse_stats = stats.to_dict()
        upload.parser_used = extractor.name
        upload.entry_count = inserted
        upload.processed_lines = stats.total_lines
        upload.status = "COMPLETED"
        upload.completed_at = datetime.now(UTC)
        AuditRepository(db).record("log.processed", user_id, None, "log_upload", str(upload_id))
        db.commit()

    @staticmethod
    def _flush(db: Session, repo: LogRepository, upload_id: int, batch: list[dict[str, Any]], done: int) -> int:
        if not batch:
            return 0
        repo.bulk_insert_entries(batch)
        upload = db.get(LogUpload, upload_id)
        assert upload is not None
        upload.processed_lines = batch[-1]["line_number"]
        db.commit()
        return len(batch)
