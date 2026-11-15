# Problem statement

Software systems emit huge volumes of logs from applications, APIs, databases, authentication and payment services and
infrastructure. During a failure, engineers read thousands of lines by hand to find the first abnormal behaviour, work out
which services are affected, judge severity, remember whether something similar happened before, and consult scattered
runbooks. This is slow, error-prone and hard to document afterwards.

IntelliOps AI targets that workflow: surface unusual activity, structure it into an incident, support the investigation
with evidence and documentation, and produce a report. It does **not** claim to identify root causes automatically. The
system distinguishes: *detected anomaly* (a statistical fact), *observed symptom*, *potential contributing factor*,
*suspected root cause* (AI/analyst hypothesis) and *confirmed root cause* (only with evidence and human confirmation, which
this version records as human notes and resolution notes, never as an automatic label).
