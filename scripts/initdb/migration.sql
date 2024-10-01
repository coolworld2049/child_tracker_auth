--ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS phone varchar(100) NULL;
--ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS code INT NULL;
--ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS token varchar(255) NULL;
--ALTER TABLE kidl.members ADD UNIQUE (phone);

ALTER TABLE kidl.devices ADD COLUMN IF NOT EXISTS avatar_url varchar(2000) NULL;

ALTER TABLE kidl.members DROP COLUMN token;
ALTER TABLE kidl.members DROP COLUMN avatar_url;

ALTER TABLE kidl.members ADD COLUMN IF NOT EXISTS region varchar(500) NULL;
