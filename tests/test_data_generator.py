from src.data_generator import generate_customers, generate_monthly_revenue


def test_generated_engagement_scores_stay_within_expected_bounds():
    customers = generate_customers(n=25)
    revenue = generate_monthly_revenue(customers, months=6)

    assert revenue["engagement_score"].between(0, 100).all()
