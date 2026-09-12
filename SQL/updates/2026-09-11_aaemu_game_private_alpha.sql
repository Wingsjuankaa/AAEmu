CREATE TABLE IF NOT EXISTS private_alpha_access (
    character_id INT UNSIGNED NOT NULL PRIMARY KEY,
    granted_by INT UNSIGNED NOT NULL,
    granted_at DATETIME NOT NULL
);
