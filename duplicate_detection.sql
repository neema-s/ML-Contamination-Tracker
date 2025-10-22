USE ml_experiment_tracker;

-- alter table to add hash + contamination flag
ALTER TABLE Data_Row
ADD COLUMN row_hash VARCHAR(64) AFTER row_data,
ADD COLUMN is_contaminated BOOLEAN DEFAULT FALSE AFTER row_hash;

-- index on row_hash for fast duplicate detection
CREATE INDEX idx_row_hash ON Data_Row(row_hash);

-- procedure to generate and store hashes for existing rows in a dataset
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