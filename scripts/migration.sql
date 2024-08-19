ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS phone varchar(100) NULL;
ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS code INT NULL;
ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS token varchar(255) NULL;
ALTER TABLE kidl.members ADD UNIQUE (phone);
