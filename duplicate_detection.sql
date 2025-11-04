USE ml_experiment_tracker;

-- Add missing column safely
SET @col_exists := (
  SELECT COUNT(*) 
  FROM INFORMATION_SCHEMA.COLUMNS 
  WHERE TABLE_NAME = 'Data_Row' AND COLUMN_NAME = 'is_contaminated'
);
SET @sql := IF(@col_exists = 0, 
  'ALTER TABLE Data_Row ADD COLUMN `is_contaminated` BOOLEAN DEFAULT FALSE AFTER `row_hash`;', 
  'SELECT "Column is_contaminated already exists";'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ensure index exists
CREATE INDEX IF NOT EXISTS idx_row_hash ON Data_Row(row_hash);

-- Drop and recreate hash generation function
DROP FUNCTION IF EXISTS generate_row_hash;
DELIMITER //
CREATE FUNCTION generate_row_hash(input TEXT)
RETURNS VARCHAR(64)
DETERMINISTIC
BEGIN
    DECLARE cleaned TEXT;
    -- Normalize text to avoid whitespace or newline differences
    SET cleaned = LOWER(TRIM(REPLACE(REPLACE(REPLACE(input, ' ', ''), '\n', ''), '\r', '')));
    RETURN SHA2(cleaned, 256);
END //
DELIMITER ;

-- Drop and recreate procedure to generate missing hashes
DROP PROCEDURE IF EXISTS generate_and_store_hashes;
DELIMITER //
CREATE PROCEDURE generate_and_store_hashes(IN p_dataset_id INT)
BEGIN
    UPDATE Data_Row
    SET row_hash = generate_row_hash(row_data)
    WHERE dataset_id = p_dataset_id 
      AND (row_hash IS NULL OR row_hash = '');
    
    SELECT CONCAT('Hashes generated for dataset_id: ', p_dataset_id) AS message;
END //
DELIMITER ;

-- Drop and recreate trigger for auto hash generation
DROP TRIGGER IF EXISTS trg_generate_hash;
DELIMITER //
CREATE TRIGGER trg_generate_hash
BEFORE INSERT ON Data_Row
FOR EACH ROW
BEGIN
    IF NEW.row_hash IS NULL OR NEW.row_hash = '' THEN
        SET NEW.row_hash = generate_row_hash(NEW.row_data);
    END IF;
END //
DELIMITER ;

-- Drop and recreate dataset health view
DROP VIEW IF EXISTS dataset_health_check;
CREATE VIEW dataset_health_check AS
SELECT 
    d.dataset_id,
    d.dataset_name,
    d.file_format,
    d.dataset_type,
    d.created_at,
    COUNT(dr.row_id) AS total_rows,
    COUNT(DISTINCT dr.row_hash) AS unique_rows,
    (COUNT(dr.row_id) - COUNT(DISTINCT dr.row_hash)) AS duplicate_rows,
    COUNT(CASE WHEN dr.is_contaminated = FALSE THEN 1 END) AS clean_rows
FROM Dataset d
LEFT JOIN Data_Row dr ON d.dataset_id = dr.dataset_id
GROUP BY d.dataset_id;

-- Drop and recreate contamination detection procedure
DROP PROCEDURE IF EXISTS detect_exact_duplicates;
DELIMITER //
CREATE PROCEDURE detect_exact_duplicates(
    IN p_train_dataset_id INT,
    IN p_test_dataset_id INT,
    IN p_report_id INT
)
BEGIN
    DECLARE overlap_count INT DEFAULT 0;

    -- Insert all contaminated rows (if any)
    INSERT INTO Contaminated_Row (
        report_id,
        row_hash,
        train_dataset_id,
        test_dataset_id,
        train_row_number,
        test_row_number
    )
    SELECT DISTINCT
        p_report_id,
        t.row_hash,
        t.dataset_id,
        s.dataset_id,
        t.row_no,
        s.row_no
    FROM Data_Row t
    INNER JOIN Data_Row s
        ON t.row_hash = s.row_hash
    WHERE t.dataset_id = p_train_dataset_id
      AND s.dataset_id = p_test_dataset_id
      AND t.row_hash IS NOT NULL
      AND s.row_hash IS NOT NULL;

    -- Mark contaminated rows in test dataset
    UPDATE Data_Row dr
    INNER JOIN Contaminated_Row cr
        ON dr.row_hash = cr.row_hash
       AND dr.dataset_id = cr.test_dataset_id
    SET dr.is_contaminated = TRUE
    WHERE dr.dataset_id = p_test_dataset_id;

    -- Return status message
    SELECT CONCAT(
        'Contamination check complete between datasets ',
        p_train_dataset_id, ' and ', p_test_dataset_id
    ) AS message;

    -- Return contamination summary
    SELECT COUNT(*) AS contaminated_rows
    FROM Contaminated_Row
    WHERE report_id = p_report_id;
END //
DELIMITER ;
