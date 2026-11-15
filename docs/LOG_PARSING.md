# Log parsing (Phase 2)

## Pipeline
`upload -> validate -> store -> (background) pass 1: parse + learn templates -> pass 2: parse + insert rows`.
Files are read line by line (long lines are cut at `LOG_MAX_LINE_LENGTH` and flagged `truncated`), so large files are never loaded into memory. Rows are inserted in batches of `LOG_BATCH_SIZE`, and `processed_lines` is updated per batch.

## Recognised formats (first match wins; custom patterns are tried first)
| Pattern | Example |
|---------|---------|
| `iso_level_bracket_service` | `2026-03-01 10:15:32,123 ERROR [payment-service] message` |
| `iso_level_service_colon` | `2026-03-01T10:15:32Z WARN auth-service: message` |
| `iso_level` | `2026-03-01 10:15:32 INFO message` |
| `bracketed_timestamp` | `[2026-03-01 10:15:32] [ERROR] svc: message` |
| `hdfs` (LogHub HDFS) | `081109 203615 148 INFO dfs.DataNode$PacketResponder: message` |
| `syslog` | `Mar  1 10:15:32 host sshd[123]: message` (no level in the format; see below) |
| CSV | columns matched by alias: timestamp/time, level/severity, service/component, host/hostname, message/msg/log/text |

Anything else is stored as-is: `level=UNKNOWN`, `service=unknown`, `hostname=unknown`, `timestamp=NULL`, and the raw line is kept in `original_message`. `host=` / `service=` tokens inside a message fill hostname/service when the format has none.

Timestamps are converted to UTC; values without a zone are **assumed to be UTC**. Syslog lines have no year (the upload year is used) and no level: the level is inferred from keywords (error, failed, warn, ...) and counted in `parse_stats.level_inferred`; this is a heuristic, not a stated level.

Custom patterns: set `LOG_PARSER_EXTRA_PATTERNS` to a JSON list of regexes with named groups from `timestamp, level, service, hostname, message` (`message` required). Invalid patterns make the app fail at startup.

## Templates
Drain3 (`LOG_TEMPLATE_MINER=drain`) learns templates; numbers, IPv4 addresses, UUIDs and hex literals are masked to `<*>`. If `drain3` cannot be imported the processor falls back to regex masking (`parser_used = regex-fallback`); `LOG_TEMPLATE_MINER=regex` forces it. Drain3 templates evolve while it learns, so the file is processed twice and every row gets the converged template. Parameters are extracted by matching the message against its template. Template id = first 12 hex chars of SHA-1 of the template text; templates are unique per user and shared across that user's uploads.

## Statistics
`parse_stats` on each upload: total/empty lines, structured vs unstructured entries, per-pattern counts, truncated lines, encoding replacements, template count, parser used, template-miner errors.

## Not verified yet
The Drain3 code path has not been executed (package unavailable in the authoring sandbox); its test is skipped unless `drain3` is installed. The Drain3 API calls used: `TemplateMiner(config=...)`, `add_log_message`, `MaskingInstruction`.
