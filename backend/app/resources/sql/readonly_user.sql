CREATE USER IF NOT EXISTS 'sql_reader'@'%' IDENTIFIED BY 'sql_reader_pass';
GRANT SELECT, SHOW VIEW ON exercise_db.* TO 'sql_reader'@'%';
FLUSH PRIVILEGES;
