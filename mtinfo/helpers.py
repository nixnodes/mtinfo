
intervals = (
    ('w', 604800),  # 60 * 60 * 24 * 7
    ('d', 86400),  # 60 * 60 * 24
    ('h', 3600),  # 60 * 60
    ('m', 60),
    ('s', 1),
    )


def fmt_time(seconds, granularity = 3):
    s = int(abs(seconds))
    result = []

    for name, count in intervals:
        value = s // count
        if value:
            s -= value * count
            result.append("{}{}".format(value if seconds > 0 else -value, name))
    return ' '.join(result[:granularity])