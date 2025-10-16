CREATE DATABASE ml_experiment_tracker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ml_experiment_tracker;

CREATE TABLE Experiment (
    experiment_id      INT AUTO_INCREMENT PRIMARY KEY,
    experiment_name    VARCHAR(255) NOT NULL,
    model_type         VARCHAR(100),
    hyperparameters    TEXT,
    accuracy           FLOAT,
    loss               FLOAT,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME ON UPDATE CURRENT_TIMESTAMP,
    description        TEXT,
    status             VARCHAR(50)
);

CREATE TABLE Model (
    model_id        INT AUTO_INCREMENT PRIMARY KEY,
    model_name      VARCHAR(255) NOT NULL,
    model_path      VARCHAR(500),
    framework       VARCHAR(100),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    description     TEXT,
    model_size      FLOAT
);

CREATE TABLE Experiment_Model (
    exp_id             INT,
    model_id           INT,
    relationship_type  VARCHAR(100),
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (exp_id, model_id),
    FOREIGN KEY (exp_id) REFERENCES Experiment(experiment_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (model_id) REFERENCES Model(model_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Dataset (
    dataset_id     INT AUTO_INCREMENT PRIMARY KEY,
    dataset_name   VARCHAR(255) NOT NULL,
    filepath       VARCHAR(500),
    filename       VARCHAR(255),
    file_format    VARCHAR(50),
    ver_no         VARCHAR(50),
    dataset_type   VARCHAR(100),
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    description    TEXT,
    filesize       FLOAT,
    checksum       VARCHAR(255)
);

CREATE TABLE Data_Row (
    row_id        INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id    INT NOT NULL,
    row_hash      VARCHAR(255),
    row_no        INT,
    row_data      TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES Dataset(dataset_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Experiment_Dataset (
    experiment_id  INT,
    data_id        INT,
    usage_type     VARCHAR(50), 
    added_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (experiment_id, data_id, usage_type),
    FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (data_id) REFERENCES Dataset(dataset_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Contamination_Report (
    report_id                  INT AUTO_INCREMENT PRIMARY KEY,
    exper_id                   INT,
    generated_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    contaminated_rows_count    INT,
    contamination_percentage   FLOAT,
    status                     VARCHAR(50),
    contamination_details      TEXT,
    FOREIGN KEY (exper_id) REFERENCES Experiment(experiment_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Contaminated_Row (
    contamination_id   INT AUTO_INCREMENT PRIMARY KEY,
    report_id          INT,
    row_hash           VARCHAR(255),
    train_dataset_id   INT,
    test_dataset_id    INT,
    train_row_number   INT,
    test_row_number    INT,
    detected_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES Contamination_Report(report_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (train_dataset_id) REFERENCES Dataset(dataset_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (test_dataset_id) REFERENCES Dataset(dataset_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);