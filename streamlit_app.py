import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="ML Contamination Tracker", layout="wide")
st.title("ML Contamination Tracker")

menu = st.sidebar.radio("Navigation", ["Upload Dataset", "Create Experiment", "View Experiments", "Detect Contamination"])

# 1. Upload Dataset
if menu == "Upload Dataset":
    st.header("Upload a CSV File")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        if st.button("Upload to Backend"):
            files = {"file": uploaded_file.getvalue()}
            try:
                response = requests.post(f"{API_URL}/upload", files={"file": (uploaded_file.name, uploaded_file, "text/csv")})
                if response.status_code == 200:
                    st.success("Upload successful!")
                    st.json(response.json())
                else:
                    st.error(f"Upload failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# 2. Create Experiment
elif menu == "Create Experiment":
    st.header("Create New Experiment")

    experiment_name = st.text_input("Experiment Name")
    model_type = st.text_input("Model Type")
    hyperparameters = st.text_area("Hyperparameters (JSON or text)")
    accuracy = st.number_input("Accuracy", min_value=0.0, max_value=1.0, step=0.01)
    loss = st.number_input("Loss", min_value=0.0, step=0.01)
    description = st.text_area("Description")
    train_dataset_id = st.number_input("Train Dataset ID", min_value=1, step=1)
    test_dataset_id = st.number_input("Test Dataset ID", min_value=1, step=1)

    # status = st.selectbox("Status", ["Pending", "Running", "Completed", "Failed"])

    if st.button("Create Experiment"):
        payload = {
            "experiment_name": experiment_name,
            "description": description,
            "model_type": model_type,
            "hyperparameters": hyperparameters,
            "train_dataset_id": train_dataset_id,
            "test_dataset_id": test_dataset_id
        }

        try:
            response = requests.post(f"{API_URL}/create_experiment", json=payload)
            if response.status_code == 200:
                st.success("Experiment created successfully!")
                st.json(response.json())
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")

# 3. View Experiments
elif menu == "View Experiments":
    st.header("Existing Experiments")
    try:
        response = requests.get(f"{API_URL}/get_experiments")
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df = df[
                    [
                        "experiment_id",
                        "experiment_name",
                        "model_type",
                        "hyperparameters",
                        "accuracy",
                        "loss",
                        "description",
                        "created_at",
                        "updated_at"
                    ]
                ]
                st.dataframe(df)
            else:
                st.info("No experiments found.")
        else:
            st.error(f"Error fetching experiments: {response.text}")
    except Exception as e:
        st.error(f"Connection error: {e}")


# 4. Detect Contamination
elif menu == "Detect Contamination":
    st.header("Run Contamination Detection")
    exper_id = st.number_input("Experiment ID", min_value=1, step=1)
    train_dataset_id = st.number_input("Train Dataset ID", min_value=1, step=1, key="train")
    test_dataset_id = st.number_input("Test Dataset ID", min_value=1, step=1, key="test")

    if st.button("Run Detection"):
        payload = {
            "exper_id": exper_id,
            "train_dataset_id": train_dataset_id,
            "test_dataset_id": test_dataset_id
        }
        try:
            response = requests.post(f"{API_URL}/detect_contamination", json=payload)
            if response.status_code == 200:
                st.success("Contamination analysis completed!")
                st.json(response.json())
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")



# import streamlit as st
# import requests

# BASE_URL = "http://127.0.0.1:8000"

# st.set_page_config(page_title="Contamination Tracker", layout="wide")

# st.title("ML Experiment Contamination Tracker")

# # Sidebar navigation
# menu = st.sidebar.radio("Navigate", ["Experiments", "Contamination Reports", "Alerts"])

# # 1. Experiments view
# if menu == "Experiments":
#     st.header("All Experiments")
#     try:
#         res = requests.get(f"{BASE_URL}/experiments")
#         if res.status_code == 200:
#             data = res.json()["experiments"]
#             if data:
#                 st.dataframe(data)
#             else:
#                 st.info("No experiments found.")
#         else:
#             st.error("Error fetching experiments.")
#     except Exception as e:
#         st.error(f"Connection error: {e}")

# # 2. Contamination Reports view
# elif menu == "Contamination Reports":
#     st.header("Check Contamination for an Experiment")
#     experiment_id = st.number_input("Enter Experiment ID", min_value=1)
#     if st.button("Fetch Report"):
#         try:
#             res = requests.get(f"{BASE_URL}/experiments/{experiment_id}/contamination")
#             if res.status_code == 200:
#                 data = res.json()
#                 st.json(data)
#             else:
#                 st.warning("No contamination report found for this experiment.")
#         except Exception as e:
#             st.error(f"Error: {e}")

# # 3. Alerts view
# elif menu == "Alerts":
#     st.header("Contamination Alerts")
#     try:
#         res = requests.get(f"{BASE_URL}/alerts")
#         if res.status_code == 200:
#             alerts = res.json()["alerts"]
#             if alerts:
#                 st.dataframe(alerts)
#             else:
#                 st.info("No contamination alerts currently.")
#         else:
#             st.error("Error fetching alerts.")
#     except Exception as e:
#         st.error(f"Connection error: {e}")
