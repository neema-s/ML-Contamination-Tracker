USE ml_experiment_tracker;

-- insert a new dataset
DELIMITER //

CREATE PROCEDURE insert_dataset(
    IN p_dataset_name VARCHAR(255),
    IN p_filepath VARCHAR(500),
    IN p_filename VARCHAR(255),
    IN p_file_format VARCHAR(50),
    IN p_dataset_type VARCHAR(100),
    IN p_description TEXT,
    IN p_filesize FLOAT,
    IN p_checksum VARCHAR(255)
)
BEGIN
    INSERT INTO Dataset (
        dataset_name, 
        filepath, 
        filename, 
        file_format, 
        dataset_type, 
        description, 
        filesize, 
        checksum
    )
    VALUES (
        p_dataset_name, 
        p_filepath, 
        p_filename, 
        p_file_format, 
        p_dataset_type, 
        p_description, 
        p_filesize, 
        p_checksum
    );
    
    SELECT 'Dataset created successfully' AS message;
    SELECT LAST_INSERT_ID() AS dataset_id;
END //

DELIMITER ;

-- get dataset information
DELIMITER //

CREATE PROCEDURE get_dataset(IN p_dataset_id INT)
BEGIN
    SELECT 
        dataset_id,
        dataset_name,
        filepath,
        filename,
        file_format,
        ver_no,
        dataset_type,
        created_at,
        description,
        filesize,
        checksum
    FROM Dataset
    WHERE dataset_id = p_dataset_id;
END //

DELIMITER ;

-- get all datasets 
DELIMITER //

CREATE PROCEDURE get_all_datasets()
BEGIN
    SELECT 
        dataset_id,
        dataset_name,
        file_format,
        dataset_type,
        created_at,
        filesize,
        (SELECT COUNT(*) FROM Data_Row WHERE dataset_id = Dataset.dataset_id) AS row_count
    FROM Dataset
    ORDER BY created_at DESC;
END //

DELIMITER ;

-- insert data row 
DELIMITER //

CREATE PROCEDURE insert_data_row(
    IN p_dataset_id INT,
    IN p_row_data TEXT,
    IN p_row_no INT
)
BEGIN
    INSERT INTO Data_Row (dataset_id, row_data, row_no)
    VALUES (p_dataset_id, p_row_data, p_row_no);
    
    SELECT 'Row inserted successfully' AS message;
    SELECT LAST_INSERT_ID() AS row_id;
END //

DELIMITER ;

-- update dataset 
DELIMITER //

CREATE PROCEDURE update_dataset(
    IN p_dataset_id INT,
    IN p_dataset_name VARCHAR(255),
    IN p_description TEXT,
    IN p_ver_no VARCHAR(50)
)
BEGIN
    UPDATE Dataset
    SET 
        dataset_name = p_dataset_name,
        description = p_description,
        ver_no = p_ver_no
    WHERE dataset_id = p_dataset_id;
    
    SELECT 'Dataset updated successfully' AS message;
END //

DELIMITER ;

-- to delete dataset 
DELIMITER //

CREATE PROCEDURE delete_dataset(IN p_dataset_id INT)
BEGIN
    DELETE FROM Dataset WHERE dataset_id = p_dataset_id;
    
    SELECT 'Dataset deleted successfully' AS message;
END //

DELIMITER ;

-- get dataset row count
DELIMITER //

CREATE PROCEDURE get_dataset_stats(IN p_dataset_id INT)
BEGIN
    SELECT 
        d.dataset_id,
        d.dataset_name,
        d.file_format,
        d.dataset_type,
        d.created_at,
        d.filesize,
        COUNT(dr.row_id) AS total_rows,
        COUNT(DISTINCT dr.row_hash) AS unique_hashes
    FROM Dataset d
    LEFT JOIN Data_Row dr ON d.dataset_id = dr.dataset_id
    WHERE d.dataset_id = p_dataset_id
    GROUP BY d.dataset_id;
END //

DELIMITER ;

-- get rows for a dataset
DELIMITER //

CREATE PROCEDURE get_dataset_rows(
    IN p_dataset_id INT,
    IN p_limit INT,
    IN p_offset INT
)
BEGIN
    SELECT 
        row_id,
        dataset_id,
        row_hash,
        row_no,
        row_data,
        created_at
    FROM Data_Row
    WHERE dataset_id = p_dataset_id
    ORDER BY row_no
    LIMIT p_limit OFFSET p_offset;
END //

DELIMITER ;
