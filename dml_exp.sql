INSERT INTO Experiment (experiment_name, model_type, hyperparameters, accuracy, loss, description, status)
VALUES 
('Image Classification Run 1', 'CNN', '{"lr":0.001,"epochs":90}', 0.91, 0.09, 'Baseline CNN model', 'completed'),
('Image Classification Run 2', 'ResNet', '{"lr":0.0005,"epochs":60}', 0.94, 0.06, 'Improved ResNet model', 'completed'),
('Text Sentiment Run 1', 'LSTM', '{"lr":0.001,"epochs":40}', 0.87, 0.13, 'Initial sentiment analysis test', 'running');

INSERT INTO Model (model_name, model_path, framework, description, model_size)
VALUES 
('CNN_Base', '/models/cnn_base_v1.h5', 'TensorFlow', 'Base CNN model for image classification', 120.4),
('ResNet50_V2', '/models/resnet50_v2.pt', 'PyTorch', 'Fine-tuned ResNet50 model', 245.9),
('LSTM_Text', '/models/lstm_text_v1.h5', 'TensorFlow', 'LSTM model for text classification', 98.2);

INSERT INTO Experiment_Model (exp_id, model_id, relationship_type)
VALUES 
(1, 1, 'training'),
(2, 2, 'validation'),
(3, 3, 'testing');

INSERT INTO Dataset (dataset_name, filepath, filename, file_format, ver_no, dataset_type, description, filesize, checksum)
VALUES
('ImageNet Subset', '/datasets/imagenet_subset.csv', 'imagenet_subset.csv', 'csv', 'v1', 'training', 'Subset of ImageNet data', 120.5, 'abc123'),
('ImageNet Augmented', '/datasets/imagenet_augmented.csv', 'imagenet_augmented.csv', 'csv', 'v2', 'validation', 'Augmented ImageNet data', 135.2, 'def456'),
('Twitter Sentiment', '/datasets/twitter_sentiment.csv', 'twitter_sentiment.csv', 'csv', 'v1', 'testing', 'Sentiment analysis dataset', 78.9, 'ghi789');

INSERT INTO Contamination_Report 
(exper_id, contaminated_rows_count, contamination_percentage, status, contamination_details)
VALUES
(1, 0, 0.0, 'Clean', 'No contamination detected'),
(2, 120, 0.02, 'Minor', 'Minor contamination found in augmented dataset'),
(3, 450, 0.15, 'High', 'High contamination — data leakage detected');



INSERT INTO Experiment (experiment_name, model_type, hyperparameters, accuracy, loss, description, status)
VALUES ('Image Classification Run 1', 'CNN', '{"lr":0.001,"epochs":50}', 0.91, 0.09, 'Baseline model', 'completed');


INSERT INTO Model (model_name, model_path, framework, description, model_size)
VALUES ('ResNet50', '/models/resnet50_v1.h5', 'TensorFlow', 'Pretrained ResNet50 model', 235.6);

UPDATE Experiment
SET status = 'running', accuracy = 0.92
WHERE experiment_name = 'Image Classification Run 1';


SELECT experiment_id, experiment_name, model_type, accuracy, status
FROM Experiment
WHERE accuracy > 0.9
ORDER BY accuracy DESC;
