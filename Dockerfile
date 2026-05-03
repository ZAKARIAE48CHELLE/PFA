FROM python:3.10-slim
WORKDIR /app
# We can just install the essentials directly in case requirements is messy
RUN pip install --default-timeout=1000 flask flask-cors joblib numpy scipy scikit-learn pandas textblob textblob-fr
COPY ml_api.py predict_offer.py ./
COPY *.pkl ./
EXPOSE 5000
CMD ["python", "ml_api.py"]
