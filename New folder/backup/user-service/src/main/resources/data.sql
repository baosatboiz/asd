INSERT INTO app_user (name, email) VALUES
('Alice Johnson', 'alice@example.com'),
('Bob Smith', 'bob@example.com'),
('Charlie Brown', 'charlie@example.com')
ON CONFLICT (email) DO NOTHING;
