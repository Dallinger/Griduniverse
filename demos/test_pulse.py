from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 1
iterations = 1

for i in range(iterations):
    data = experiment.run(
        time_per_round=120.0,
        mode="live",
        max_participants=participants,
        num_recruits=participants * 3,
        num_dynos_worker=1,
        recruiter="pulse",
        us_only=False,
        dyno_type="performance-l",
        redis_size="premium-5",
        workers="auto",
        base_payment=1.0,
        dollars_per_point=0.02,
        title="Griduniverse game",
        description="Play a simple web game and earn an extra $0.02 per point",
        pulse_image_url="https://i.imgur.com/8oduFt9.png",
        pulse_page_id="179429022790771",
        pulse_reward_processor="TransferTo",
        pulse_reward_currency="Airtime",
        pulse_privacy_link="https://www.istresearch.com/privacy",
        pulse_location="http://sws.geonames.org/6252001",
        pulse_api_url="https://r4wwzub23l.execute-api.us-east-1.amazonaws.com/ngs2",
    )

    results = experiment.analyze(data)
    print(results)

print(
    "Script successfully ran with %d participants for %d iterations"
    % (participants, iterations)
)
