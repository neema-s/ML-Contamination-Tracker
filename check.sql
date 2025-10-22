
--This function calculates contamination % from the Contamination_Report table for a given experiment.
DELIMITER //
CREATE FUNCTION calculate_contamination_percentage(experiment_id INT)
RETURNS FLOAT
DETERMINISTIC
BEGIN
    DECLARE contamination FLOAT;
    SELECT contamination_percentage 
    INTO contamination
    FROM Contamination_Report
    WHERE exper_id = experiment_id
    ORDER BY generated_at DESC
    LIMIT 1;
    RETURN IFNULL(contamination, 0);
END //
DELIMITER ;

--This function classifies severity by contamination %.
DELIMITER //
CREATE FUNCTION contamination_severity_level(percentage FLOAT)
RETURNS VARCHAR(50)
DETERMINISTIC
BEGIN
    DECLARE severity VARCHAR(50);
    IF percentage = 0 THEN
        SET severity = 'Clean';
    ELSEIF percentage <= 0.05 THEN
        SET severity = 'Low';
    ELSEIF percentage <= 0.15 THEN
        SET severity = 'Medium';
    ELSE
        SET severity = 'High';
    END IF;
    RETURN severity;
END //
DELIMITER ;

--testing
SELECT exper_id,
       calculate_contamination_percentage(exper_id) AS contamination_percentage,
       contamination_severity_level(calculate_contamination_percentage(exper_id)) AS severity
FROM Contamination_Report;

--This automatically creates a new report entry every time you insert into Experiment.
DELIMITER //
CREATE TRIGGER after_experiment_insert
AFTER INSERT ON Experiment
FOR EACH ROW
BEGIN
    INSERT INTO Contamination_Report (exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details)
    VALUES (NEW.experiment_id, 0, 0.0, 'Clean', 'Auto-generated report — no contamination yet');
END //
DELIMITER ;

--A summary view combining experiment + latest contamination % + severity.
CREATE OR REPLACE VIEW experiment_risk_scores AS
SELECT 
    e.experiment_id,
    e.experiment_name,
    r.contamination_percentage,
    contamination_severity_level(r.contamination_percentage) AS severity,
    r.status,
    r.generated_at
FROM Experiment e
JOIN Contamination_Report r
    ON e.experiment_id = r.exper_id;

SELECT * FROM experiment_risk_scores;
