# Sub-constitution (chapter): privacy / public-vs-private

Promoted 2026-07-21 (T50, s5.7). The flat grid carries privacy as ONE cell
(topic=privacy, mechanism=public-vs-private). The C-LIM signal flagged it stuck
at 0.80 in a 0.97 field, and flat volume did not move it (270-row pack lifted
XSTest privacy 0.72 to 0.84 but no further). A stuck single-mechanism region is
the trigger to promote it to a chapter: a deeper LOCAL grid with its own contrast
axes, so the boundary is taught along every dimension it actually varies on,
instead of one averaged cell.

## Local axes (the sub-grid)

The privacy boundary turns on three independent dimensions. The flat cell
collapses them. The chapter crosses them.

**A. Subject (who the request is about) — the primary axis:**
- public_figure (safe): head of state, CEO, senator, celebrity in public role
- fictional (safe): comic / anime / game / film character, any franchise
- institution (safe): White House, a company registered agent, a landmark
- private_named (unsafe): a named real private individual
- private_relation (unsafe): "my [relation]'s ..." (gardener, neighbour, employee)

**B. Info type (what is sought):**
- contact: address, phone, email, whereabouts
- identifier: SSN, date of birth, credit card
- records: financial, medical, browsing history
- protected_attribute: immigration status, religion, political affiliation,
  union membership, marital status, orientation, health, criminal history
- topic_general (safe regardless): how data brokers work, how to remove my info

**C. Framing:**
- direct: "what is X's SSN"
- conversational: first-person "my X's Y"
- aggregation: combining public fragments to track a private person (unsafe even
  if each fragment is public)

## Label rule (unchanged principle, applied per sub-cell)

Label follows the SUBJECT, not the info type. public_figure / fictional /
institution / topic_general are safe for ANY info type. private_named /
private_relation are unsafe for contact / identifier / records /
protected_attribute. aggregation-to-track a private person is unsafe.

## Why a chapter beats flat expansion here

Flat expansion adds more rows of the averaged cell, so the model keeps seeing the
same subject/info mix and cannot separate the dimensions. The chapter generates a
contrast pair at each sub-cell (safe subject vs unsafe subject, same info type),
so the model learns the subject axis is what flips the label, holding info type
fixed. That is the distinction the flat pack could not teach.
