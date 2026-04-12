-- ============================================================
-- SOAP Note Application - Database Schema
-- Sprint 1
-- ============================================================

-- 1. Transcripts: stores audio file info and raw transcript text
CREATE TABLE transcripts (
    id               SERIAL PRIMARY KEY,
    audio_filename   VARCHAR(255) NOT NULL,
    raw_transcript_text TEXT NOT NULL,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookup by filename
CREATE INDEX idx_transcripts_audio_filename ON transcripts(audio_filename);


-- 2. Generated Notes: stores GPT-4 generated SOAP note sections
CREATE TABLE generated_notes (
    id                  SERIAL PRIMARY KEY,
    transcript_id       INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    subjective          TEXT,
    objective           TEXT,
    assessment          TEXT,
    plan                TEXT,
    raw_gpt4_response   TEXT
);

-- Index for joining with transcripts
CREATE INDEX idx_generated_notes_transcript_id ON generated_notes(transcript_id);


-- 3. Physician Edits: tracks every edit a physician makes to a SOAP section
CREATE TABLE physician_edits (
    id              SERIAL PRIMARY KEY,
    note_id         INTEGER NOT NULL REFERENCES generated_notes(id) ON DELETE CASCADE,
    section_edited  VARCHAR(50) NOT NULL,   -- 'subjective' | 'objective' | 'assessment' | 'plan'
    edited_text     TEXT NOT NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for joining with generated_notes
CREATE INDEX idx_physician_edits_note_id ON physician_edits(note_id);


-- 4. Audit Log: records all actions taken on notes
CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    note_id         INTEGER NOT NULL REFERENCES generated_notes(id) ON DELETE CASCADE,
    action_taken    VARCHAR(255) NOT NULL,  -- e.g. 'note_generated', 'note_edited', 'note_approved'
    who             VARCHAR(255) NOT NULL,  -- physician username or system
    "when"          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for joining with generated_notes
CREATE INDEX idx_audit_log_note_id ON audit_log(note_id);
