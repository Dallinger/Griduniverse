from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 1
iterations = 1

for i in range(iterations):
    data = experiment.run(
        time_per_round = 120.0,
        mode=u'live',
        max_participants=participants,
        num_recruits=participants*3,
        num_dynos_worker=1,
        recruiter=u'pulse',
        us_only=False,
        dyno_type=u"performance-l",
        redis_size=u"premium-5",
        workers="auto",
        base_payment=1.0,
        dollars_per_point=0.02,
        title="Griduniverse game",
        description="Play a simple web game and earn an extra $0.02 per point",
        pulse_image_url=u"https://i.imgur.com/8oduFt9.png",
        pulse_page_id=u'179429022790771',
        pulse_reward_processor=u'TransferTo',
        pulse_reward_currency=u'Airtime',
        pulse_privacy_link=u"https://www.istresearch.com/privacy",
        pulse_location=u"http://sws.geonames.org/6252001",
        pulse_api_url=u"https://r4wwzub23l.execute-api.us-east-1.amazonaws.com/ngs2",
    )

    results = experiment.analyze(data)
    print(results)

print("Script successfully ran with %d participants for %d iterations" % (participants, iterations))

