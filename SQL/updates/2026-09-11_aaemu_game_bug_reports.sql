CREATE TABLE IF NOT EXISTS bug_reports (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
 created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 account_id INT UNSIGNED NOT NULL,
 character_id INT UNSIGNED NOT NULL,
 character_name VARCHAR(128) NOT NULL,
 request_key VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 category VARCHAR(24) CHARACTER SET ascii NOT NULL,
 entity_id INT UNSIGNED NOT NULL DEFAULT 0,
 entity_name VARCHAR(1024) NOT NULL DEFAULT '',
 detail TEXT NOT NULL,
 fingerprint CHAR(64) CHARACTER SET ascii NOT NULL,
 context_json JSON NOT NULL,
 status VARCHAR(24) CHARACTER SET ascii NOT NULL DEFAULT 'new',
 developer_notes TEXT NULL,
 UNIQUE KEY uq_report_request (character_id, request_key),
 KEY ix_report_queue (status, category, created_at),
 KEY ix_report_entity (category, entity_id),
 KEY ix_report_account_time (account_id, created_at),
 KEY ix_report_fingerprint (fingerprint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bug_report_updates (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
 report_id BIGINT UNSIGNED NOT NULL,
 created_at DATETIME(6) NOT NULL,
 status VARCHAR(24) CHARACTER SET ascii NOT NULL,
 note TEXT NOT NULL,
 KEY ix_report_history (report_id, id),
 CONSTRAINT fk_bug_report_update FOREIGN KEY(report_id) REFERENCES bug_reports(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
