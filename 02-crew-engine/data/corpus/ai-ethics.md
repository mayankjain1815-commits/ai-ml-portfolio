# AI Ethics and Risks, Without the Panic

The most immediate AI risks are not science fiction; they are statistical.
Bias is the classic one: models trained on historical data inherit its
prejudices, so a hiring model trained on old decisions can systematically
favor one demographic group. Because models are black boxes, such bias can
hide for a long time before anyone measures the model's errors across
different groups.

Hallucination is a second real risk. Large language models generate
plausible text without a built-in truth check, so they confidently invent
facts, citations, and code when the answer is not in their training data.
The standard defense is retrieval: ground the model in documents you
control and force it to cite passages, so the answer can be checked.

Privacy and consent matter too. Models trained on scraped data can
memorize personal information; systems that process sensitive input need
clear data policies, encryption, and the right to deletion.

Finally, automation shifts who does what. The evidence so far suggests AI
augments most knowledge work rather than eliminating it: it removes the
mechanical parts, but decisions still land with people. The responsible
practices, boring but effective, are: measure bias, ground answers in
sources, log decisions, and keep a human accountable for anything the
model suggests.