run:
	python main.py

validate:
	python validate.py

clean:
	rm -f affiliate_features.json classifications.json quality_scores.json \
	      quality_score_model.md payouts.json llm_calls.jsonl \
	      adversarial_review.json ltv_forecast.json \
	      affiliate_communications.md detection_rules.md
	rm -rf justifications/

all: run validate
