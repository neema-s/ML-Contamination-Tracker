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

-- to delete dataset 
DELIMITER //

CREATE PROCEDURE delete_dataset(IN p_dataset_id INT)
BEGIN
    DELETE FROM Dataset WHERE dataset_id = p_dataset_id;
    
    SELECT 'Dataset deleted successfully' AS message;
END //

DELIMITER ;

DELIMITER //
CREATE PROCEDURE create_experiment(
    IN p_experiment_name VARCHAR(255),
    IN p_description TEXT,
    IN p_model_type VARCHAR(100),
    IN p_hyperparameters TEXT,
    IN p_status VARCHAR(50),
    IN p_train_dataset_id INT,
    IN p_test_dataset_id INT
)
BEGIN
    DECLARE v_experiment_id INT;

    INSERT INTO Experiment (
        experiment_name,
        description,
        model_type,
        hyperparameters,
        status,
        created_at
    )
    VALUES (
        p_experiment_name,
        p_description,
        p_model_type,
        p_hyperparameters,
        p_status,
        NOW()
    );
    SET v_experiment_id = LAST_INSERT_ID();

    INSERT INTO Experiment_Dataset (experiment_id, data_id, usage_type)
    VALUES (v_experiment_id, p_train_dataset_id, 'train'),
           (v_experiment_id, p_test_dataset_id, 'test');

    SELECT 'Experiment created successfully' AS message;
    SELECT v_experiment_id AS experiment_id;
END //
DELIMITER ;

DROP PROCEDURE IF EXISTS get_all_experiments;
DELIMITER //
CREATE PROCEDURE get_all_experiments()
BEGIN
    SELECT 
        e.experiment_id,
        e.experiment_name,
        e.model_type,
        e.hyperparameters,
        e.accuracy,
        e.loss,
        e.created_at,
        e.updated_at,
        e.description,
        ed.usage_type,
        d.dataset_name
    FROM Experiment e
    LEFT JOIN Experiment_Dataset ed ON e.experiment_id = ed.experiment_id
    LEFT JOIN Dataset d ON ed.data_id = d.dataset_id
    ORDER BY e.experiment_id;
END //
DELIMITER ;
