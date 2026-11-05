-- M8-T1: what the verifier found in the model's first draft, before any re-ask.
-- JSON written by agent.review.first_review_record. NULL means the narrative was
-- drafted before this was recorded (or came from an older cache entry).
ALTER TABLE narrative ADD COLUMN IF NOT EXISTS first_review JSON;
