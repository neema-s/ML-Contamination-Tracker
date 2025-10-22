-- Mock contamination reports
INSERT INTO Contamination_Report (exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details)
VALUES
(1, 0, 0.0, 'Clean', 'No contamination detected'),
(2, 5, 2.5, 'Low Risk', 'Minor contamination detected'),
(3, 15, 15.0, 'Medium Risk', 'Moderate contamination detected');

-- Mock contaminated rows
INSERT INTO Contaminated_Row (report_id, row_hash, train_dataset_id, test_dataset_id, train_row_number, test_row_number)
VALUES
(2, 'hash123', 1, 2, 10, 20),
(2, 'hash124', 1, 2, 11, 21),
(3, 'hash125', 2, 3, 5, 15),
(3, 'hash126', 2, 3, 6, 16),
(3, 'hash127', 2, 3, 7, 17);

--generate contamination report
DELIMITER //
CREATE PROCEDURE generate_contamination_report(IN experimentId INT)
BEGIN
    DECLARE contaminatedCount INT DEFAULT 0;
    DECLARE totalRows INT DEFAULT 100; -- set mock total rows if needed
    DECLARE contaminationPercent FLOAT DEFAULT 0;

    SELECT COUNT(*) INTO contaminatedCount
    FROM Contaminated_Row cr
    JOIN Contamination_Report r ON cr.report_id = r.report_id
    WHERE r.exper_id = experimentId;

    IF totalRows > 0 THEN
        SET contaminationPercent = (contaminatedCount / totalRows) * 100;
    END IF;

    INSERT INTO Contamination_Report (exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details)
    VALUES (experimentId, contaminatedCount, contaminationPercent,
            CASE
                WHEN contaminationPercent = 0 THEN 'Clean'
                WHEN contaminationPercent <= 5 THEN 'Low Risk'
                WHEN contaminationPercent <= 15 THEN 'Medium Risk'
                ELSE 'High Risk'
            END,
            CONCAT('Detected ', contaminatedCount, ' contaminated rows.'));
END //
DELIMITER ;

--analyze patterns
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
DELIMITER //
CREATE PROCEDURE flag_high_risk_experiments(IN riskThreshold FLOAT)
BEGIN
    UPDATE Contamination_Report
    SET status = 'High Risk'
    WHERE contamination_percentage > riskThreshold;
END //
DELIMITER ;


-- testing
-- Generate report for experiment 1, 2, 3
CALL generate_contamination_report(1);
CALL generate_contamination_report(2);
CALL generate_contamination_report(3);

-- Analyze contamination patterns for experiment 3
CALL analyze_contamination_patterns(3);

-- Flag all experiments above 10% contamination
CALL flag_high_risk_experiments(10);

-- View all contamination reports
SELECT * FROM Contamination_Report;
