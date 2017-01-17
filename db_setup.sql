CREATE TABLE IF NOT EXISTS subscriptions (
	id INT IDENTITY(1,1) PRIMARY KEY NOT NULL,
	op_id TEXT NOT NULL,
	subscriber_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_id_to_name (
	user_id TEXT NOT NULL UNIQUE,
	display_name TEXT NOT NULL
);
