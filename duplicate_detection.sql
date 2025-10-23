USE ml_experiment_tracker;

-- alter table to add hash + contamination flag
ALTER TABLE Data_Row
ADD COLUMN IF NOT EXISTS `is_contaminated` BOOLEAN DEFAULT FALSE AFTER `row_hash`;

-- index on row_hash for fast duplicate detection
CREATE INDEX idx_row_hash ON Data_Row(row_hash);

-- function to generate hash
DROP FUNCTION IF EXISTS generate_row_hash;
DELIMITER //

CREATE FUNCTION generate_row_hash(input TEXT)
RETURNS VARCHAR(64)
DETERMINISTIC
BEGIN
    RETURN SHA2(input, 256);
END //

DELIMITER ;

-- procedure to generate and store hashes for existing rows in a dataset
DROP PROCEDURE IF EXISTS generate_and_store_hashes;
DELIMITER //

CREATE PROCEDURE generate_and_store_hashes(IN p_dataset_id INT)
BEGIN
    UPDATE Data_Row
    SET row_hash = generate_row_hash(row_data)
    WHERE dataset_id = p_dataset_id AND (row_hash IS NULL OR row_hash = '');
    
    SELECT CONCAT('Hashes generated for dataset_id: ', p_dataset_id) AS message;
END //

DELIMITER ;

-- trigger to auto_generate hash on new row insert
DROP TRIGGER IF EXISTS trg_generate_hash;
DELIMITER //

CREATE TRIGGER trg_generate_hash
BEFORE INSERT ON Data_Row
FOR EACH ROW
BEGIN
    SET NEW.row_hash = generate_row_hash(NEW.row_data);
END //

DELIMITER ;

-- dataset health check
CREATE OR REPLACE VIEW dataset_health_check AS
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

-- procedure to detect exact duplicates between datasets
DROP PROCEDURE IF EXISTS detect_exact_duplicates;
DELIMITER //

CREATE PROCEDURE detect_exact_duplicates(
    IN p_train_dataset_id INT,
    IN p_test_dataset_id INT,
    IN p_report_id INT  
)
BEGIN
    INSERT INTO Contaminated_Row (report_id, row_hash, train_dataset_id, test_dataset_id, train_row_number, test_row_number)
    SELECT p_report_id, t.row_hash, t.dataset_id, s.dataset_id, t.row_no, s.row_no
    FROM Data_Row t
    JOIN Data_Row s
      ON t.row_hash = s.row_hash
     AND t.dataset_id = p_train_dataset_id
     AND s.dataset_id = p_test_dataset_id;

    UPDATE Data_Row dr
    JOIN Contaminated_Row cr
      ON dr.row_hash = cr.row_hash
     AND dr.dataset_id = cr.test_dataset_id
    SET dr.is_contaminated = TRUE
    WHERE dr.dataset_id = p_test_dataset_id;

    SELECT CONCAT('Contamination check complete between datasets ',
                  p_train_dataset_id, ' and ', p_test_dataset_id) AS message;
END //

DELIMITER ;