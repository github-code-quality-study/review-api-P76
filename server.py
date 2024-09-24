import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, unquote
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from flask import Flask, request
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """
        allowed_locations = [
            "Albuquerque, New Mexico",
            "Carlsbad, California",
            "Chula Vista, California",
            "Colorado Springs, Colorado",
            "Denver, Colorado",
            "El Cajon, California",
            "El Paso, Texas",
            "Escondido, California",
            "Fresno, California",
            "La Mesa, California",
            "Las Vegas, Nevada",
            "Los Angeles, California",
            "Oceanside, California",
            "Phoenix, Arizona",
            "Sacramento, California",
            "Salt Lake City, Utah",
            "San Diego, California",
            "Tucson, Arizona"
        ]
        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            response_body = json.loads(response_body.decode("utf-8"))
            for item in response_body:
                item['sentiment'] = self.analyze_sentiment(item.get('ReviewBody'))

            query_string = environ.get('QUERY_STRING', '')
            if query_string:
                
                query_params = parse_qs(query_string)

                location = unquote(query_params.get('location', [''])[0])
                start_date = query_params.get('start_date', [''])[0]
                end_date = query_params.get('end_date', [''])[0]
                print(start_date)
                print(end_date)
  
                if start_date:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                if end_date:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                response_body = [
                    item for item in response_body 
                    if (location is None or item.get('Location') == location and location in allowed_locations) and 
                    (start_date == '' or datetime.strptime(item.get('Timestamp'), '%Y-%m-%d %H:%M:%S') >= start_date) and
                    (end_date == '' or datetime.strptime(item.get('Timestamp'), '%Y-%m-%d %H:%M:%S') <= end_date)
                    
                ]

            response_body = sorted(response_body, key=lambda x: x['sentiment']['compound'], reverse=True)
            response_body = json.dumps(response_body, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(content_length)
            decoded_string = request_body.decode('utf-8')

            parsed_data = parse_qs(decoded_string)
            parsed_data = {k: v[0] for k, v in parsed_data.items()}

            review_body = parsed_data.get('ReviewBody')
            location = parsed_data.get('Location')

            if not review_body:
                start_response("400 Bad Request", [("Content-Type", "text/plain")])
                return [b"ReviewBody is required"]

            if not location:
                start_response("400 Bad Request", [("Content-Type", "text/plain")])
                return [b"Location is required"]

            if location not in allowed_locations:
                start_response("400 Bad Request", [("Content-Type", "text/plain")])
                return [b"Invalid location"]
            
            # Generate Timestamp and ReviewId
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            review_id = str(uuid.uuid4())
            
            # Create the review dictionary
            review = {
                "ReviewId": review_id,
                "ReviewBody": review_body,
                "Location": location,
                "Timestamp": timestamp
            }
            
            # Convert the review to a JSON byte string
            response_body = json.dumps(review, indent=2).encode("utf-8")
            
            # Set the appropriate response headers
            start_response("201 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            
            return [response_body]

        
if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()