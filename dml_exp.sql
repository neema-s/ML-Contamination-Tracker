INSERT INTO Experiment (experiment_name, model_type, hyperparameters, accuracy, loss, description, status)
VALUES ('Image Classification Run 1', 'CNN', '{"lr":0.001,"epochs":50}', 0.91, 0.09, 'Baseline model', 'completed');


INSERT INTO Model (model_name, model_path, framework, description, model_size)
VALUES ('ResNet50', '/models/resnet50_v1.h5', 'TensorFlow', 'Pretrained ResNet50 model', 235.6);

UPDATE Experiment
SET status = 'running', accuracy = 0.92
WHERE experiment_name = 'Image Classification Run 1';

DELETE FROM Model
WHERE model_name = 'Old_Model_V1';

SELECT experiment_id, experiment_name, model_type, accuracy, status
FROM Experiment
WHERE accuracy > 0.9
ORDER BY accuracy DESC;
