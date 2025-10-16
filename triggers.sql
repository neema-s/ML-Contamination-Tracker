-- Automatically update the updated_at timestamp on experiment changes

DELIMITER //
CREATE TRIGGER auto_update_experiment_timestamp
BEFORE UPDATE ON experiment
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END //
DELIMITER ;

-- Ensure contamination percentage is valid before insert

DELIMITER //
CREATE TRIGGER validate_contamination_percentage
BEFORE INSERT ON contamination_report
FOR EACH ROW
BEGIN
    IF NEW.contamination_percentage < 0 OR NEW.contamination_percentage > 100 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Contamination percentage must be between 0 and 100';
    END IF;
END //
DELIMITER ;

-- Automatically set severity level based on contamination percentage

DELIMITER //
CREATE TRIGGER auto_set_severity_level
BEFORE INSERT ON contamination_report
FOR EACH ROW
BEGIN
    IF NEW.contamination_percentage = 0 THEN
        SET NEW.severity_level = 'none';
        SET NEW.status = 'clean';
    ELSEIF NEW.contamination_percentage <= 5 THEN
        SET NEW.severity_level = 'low';
        SET NEW.status = 'contaminated';
    ELSEIF NEW.contamination_percentage <= 10 THEN
        SET NEW.severity_level = 'medium';
        SET NEW.status = 'contaminated';
    ELSEIF NEW.contamination_percentage <= 20 THEN
        SET NEW.severity_level = 'high';
        SET NEW.status = 'contaminated';
    ELSE
        SET NEW.severity_level = 'critical';
        SET NEW.status = 'critical';
    END IF;
END //
DELIMITER ;

-- Update dataset row count when rows are added or deleted

DELIMITER //
CREATE TRIGGER update_dataset_row_count_insert
AFTER INSERT ON data_row
FOR EACH ROW
BEGIN
    UPDATE dataset
    SET row_count = row_count + 1
    WHERE dataset_id = NEW.dataset_id;
END //
DELIMITER ;

DELIMITER //
CREATE TRIGGER update_dataset_row_count_delete
AFTER DELETE ON data_row
FOR EACH ROW
BEGIN
    UPDATE dataset
    SET row_count = row_count - 1
    WHERE dataset_id = OLD.dataset_id;
END //
DELIMITER ;

-- Automatically create a pending contamination report when experiment is created

DELIMITER //
CREATE TRIGGER auto_create_contamination_report
AFTER INSERT ON experiment
FOR EACH ROW
BEGIN
    INSERT INTO contamination_report (exper_id, status, severity_level)
    VALUES (NEW.experiment_id, 'pending', 'none');
END //
DELIMITER ;
