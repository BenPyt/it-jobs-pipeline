-- Luoc do CSDL cho pipeline tin tuyen dung IT
-- Thiet ke chuan hoa: mot tin co nhieu ky nang / nhieu dia diem -> tach bang rieng.

CREATE TABLE IF NOT EXISTS crawl_runs (
    run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    sources      TEXT,
    n_raw        INTEGER DEFAULT 0,
    n_clean      INTEGER DEFAULT 0,
    status       TEXT DEFAULT 'running',
    note         TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_key           TEXT PRIMARY KEY,     -- '<source>:<id>'
    source            TEXT NOT NULL,
    source_job_id     TEXT NOT NULL,
    url               TEXT,
    title             TEXT NOT NULL,
    title_clean       TEXT,
    company           TEXT,
    company_key       TEXT,
    seniority         TEXT,
    location_primary  TEXT,
    work_arrangement  TEXT,
    salary_raw        TEXT,
    salary_min_vnd    REAL,
    salary_max_vnd    REAL,
    salary_mid_vnd    REAL,
    salary_currency   TEXT,
    salary_disclosed  INTEGER DEFAULT 0,
    n_skills          INTEGER DEFAULT 0,
    n_sources         INTEGER DEFAULT 1,
    sources           TEXT,
    posted_raw        TEXT,
    description_raw   TEXT,
    first_seen_at     TEXT NOT NULL,        -- lan dau nhin thay tin nay
    last_seen_at      TEXT NOT NULL,        -- lan crawl gan nhat con thay
    run_id            INTEGER REFERENCES crawl_runs(run_id)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_key  TEXT NOT NULL REFERENCES jobs(job_key) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    PRIMARY KEY (job_key, skill_id)
);

CREATE TABLE IF NOT EXISTS job_locations (
    job_key  TEXT NOT NULL REFERENCES jobs(job_key) ON DELETE CASCADE,
    location TEXT NOT NULL,
    PRIMARY KEY (job_key, location)
);

CREATE INDEX IF NOT EXISTS idx_jobs_source       ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_seniority    ON jobs(seniority);
CREATE INDEX IF NOT EXISTS idx_jobs_location     ON jobs(location_primary);
CREATE INDEX IF NOT EXISTS idx_jobs_company      ON jobs(company_key);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen    ON jobs(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill  ON job_skills(skill_id);
