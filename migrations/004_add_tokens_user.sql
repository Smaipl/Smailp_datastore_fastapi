-- Add tokens_user column to logs table with existence check
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 
    FROM information_schema.columns 
    WHERE table_name = 'logs' AND column_name = 'tokens_user'
  ) THEN
    ALTER TABLE logs ADD COLUMN tokens_user BIGINT;
  END IF;
END $$;