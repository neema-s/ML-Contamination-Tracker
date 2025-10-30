--This function calculates contamination % from the Contamination_Report table for a given experiment.
DELIMITER //
CREATE FUNCTION calculate_contamination_percentage(experiment_id INT)
RETURNS FLOAT
DETERMINISTIC
BEGIN
    DECLARE contamination FLOAT DEFAULT 0;
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


--This automatically creates a new report entry every time you insert into Experiment.
DELIMITER //
CREATE TRIGGER after_experiment_insert
AFTER INSERT ON Experiment
FOR EACH ROW
BEGIN
    INSERT INTO Contamination_Report 
        (exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details)
    VALUES 
        (NEW.experiment_id, 0, 0.0, 'Clean', 'Auto-generated report — no contamination yet');
END //
DELIMITER ;


--A summary view combining experiment + latest contamination % + severity.
CREATE OR REPLACE VIEW experiment_risk_scores AS
SELECT 
    e.experiment_id,
    e.experiment_name,
    e.model_type,
    r.contamination_percentage,
    contamination_severity_level(r.contamination_percentage) AS severity,
    r.status,
    r.generated_at
FROM Experiment e
JOIN (
    SELECT exper_id, contamination_percentage, status, generated_at
    FROM Contamination_Report AS cr
    WHERE generated_at = (
        SELECT MAX(generated_at)
        FROM Contamination_Report
        WHERE exper_id = cr.exper_id
    )
) AS r
ON e.experiment_id = r.exper_id;


-- Check summarized risk data
-- Check contamination percentage and severity per report
SELECT 
    exper_id,
    calculate_contamination_percentage(exper_id) AS contamination_percentage,
    contamination_severity_level(calculate_contamination_percentage(exper_id)) AS severity
FROM Contamination_Report;

-- Check summarized risk data
SELECT * FROM experiment_risk_scores;


