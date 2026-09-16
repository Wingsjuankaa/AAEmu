-- Apply to aaemu_game before deploying the account-aware Game backend.
-- No character grants are copied: account revocation remains effective.
CREATE TABLE IF NOT EXISTS private_alpha_account_access (
    account_id INT UNSIGNED NOT NULL PRIMARY KEY,
    granted_by INT UNSIGNED NOT NULL,
    granted_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
