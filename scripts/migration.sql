ALTER TABLE kidl.members ADD phone varchar(100) NULL;
ALTER TABLE kidl.members ADD code INT NULL;
ALTER TABLE kidl.members ADD token varchar(255) NULL;
ALTER TABLE kidl.members ADD UNIQUE (phone);
