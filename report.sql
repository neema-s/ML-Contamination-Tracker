-- Contamination report generator: finds linked train/test datasets for an experiment,
-- runs exact duplicate detection, and summarizes into Contamination_Report
USE ml_experiment_tracker;

DROP PROCEDURE IF EXISTS generate_contamination_report;
DELIMITER //
CREATE PROCEDURE generate_contamination_report(IN experimentId INT)
BEGIN
    DECLARE trainId INT;
    DECLARE testId INT;
    DECLARE newReportId INT;
    DECLARE contaminatedCount INT DEFAULT 0;
    DECLARE totalTestRows INT DEFAULT 0;
    DECLARE contaminationPercent FLOAT DEFAULT 0;

    -- Resolve linked datasets for this experiment
    SELECT data_id INTO trainId
    FROM Experiment_Dataset
    WHERE experiment_id = experimentId AND usage_type = 'train'
    ORDER BY added_at DESC
    LIMIT 1;

    SELECT data_id INTO testId
    FROM Experiment_Dataset
    WHERE experiment_id = experimentId AND usage_type = 'test'
    ORDER BY added_at DESC
    LIMIT 1;

    IF trainId IS NULL OR testId IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Train or test dataset not linked to this experiment';
    END IF;

    -- Create a new report stub and capture its ID
    INSERT INTO Contamination_Report (
        exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details
    ) VALUES (
        experimentId, 0, 0.0, 'running', CONCAT('Checking contamination between datasets ', trainId, ' and ', testId)
    );
    SET newReportId = LAST_INSERT_ID();

    -- Populate Contaminated_Row using exact duplicates by hash
    CALL detect_exact_duplicates(trainId, testId, newReportId);

    -- Compute counts and percentage
    SELECT COUNT(*) INTO contaminatedCount FROM Contaminated_Row WHERE report_id = newReportId;
    SELECT COUNT(*) INTO totalTestRows FROM Data_Row WHERE dataset_id = testId;

    IF totalTestRows > 0 THEN
        SET contaminationPercent = (contaminatedCount / totalTestRows) * 100;
    ELSE
        SET contaminationPercent = 0.0;
    END IF;

    -- Finalize report status and details
    UPDATE Contamination_Report
    SET contaminated_rows_count = contaminatedCount,
        contamination_percentage = contaminationPercent,
        status = CASE
            WHEN contaminationPercent = 0 THEN 'Clean'
            WHEN contaminationPercent <= 5 THEN 'Low Risk'
            WHEN contaminationPercent <= 15 THEN 'Medium Risk'
            ELSE 'High Risk'
        END,
        contamination_details = CONCAT('Detected ', contaminatedCount, ' contaminated rows between datasets ', trainId, ' and ', testId)
    WHERE report_id = newReportId;

    -- Return the finalized report summary
    SELECT newReportId AS report_id,
           experimentId AS exper_id,
           trainId AS train_dataset_id,
           testId AS test_dataset_id,
           contaminatedCount AS contaminated_rows_count,
           contaminationPercent AS contamination_percentage;
END //
DELIMITER ;

--analyze patterns
DROP PROCEDURE IF EXISTS analyze_contamination_patterns;
DELIMITER //
CREATE PROCEDURE analyze_contamination_patterns(IN experimentId INT)
BEGIN
    SELECT 
        cr.train_dataset_id,
        cr.test_dataset_id,
        COUNT(cr.row_hash) AS overlapping_rows,
        MIN(cr.detected_at) AS first_detected,
        MAX(cr.detected_at) AS last_detected
    FROM Contaminated_Row cr
    JOIN Contamination_Report r ON cr.report_id = r.report_id
    WHERE r.exper_id = experimentId
    GROUP BY cr.train_dataset_id, cr.test_dataset_id
    ORDER BY overlapping_rows DESC;
END //
DELIMITER ;

--flag high risk procedures
DROP PROCEDURE IF EXISTS flag_high_risk_experiments;
DELIMITER //
CREATE PROCEDURE flag_high_risk_experiments(IN riskThreshold FLOAT)
BEGIN
    UPDATE Contamination_Report
    SET status = 'High Risk'
    WHERE contamination_percentage > riskThreshold;
END //
DELIMITER ;


-- testing (manual only)
-- CALL generate_contamination_report(1);
-- CALL analyze_contamination_patterns(3);
-- CALL flag_high_risk_experiments(10);
-- SELECT * FROM Contamination_Report;
