import datetime
from enum import Enum


class DatetimeFormats(Enum):
    DATE_NUM = "{date_num}"  # 2014-02-18
    DATE = "{date}"  # February 18th, 2014
    DATE_SHORT = "{date_short}"  # Feb 18, 2014
    DATE_LONG = "{date_long}"  # Tuesday, February 18th, 2014
    DATE_PRETTY = "{date_pretty}"  # date but uses "yesterday", "today", or "tomorrow" where appropriate # noqa: E501
    DATE_SHORT_PRETTY = "{date_short_pretty}"  # date_short but uses "yesterday", "today", or "tomorrow" where appropriate # noqa: E501
    DATE_LONG_PRETTY = "{date_long_pretty}"  # date_long but uses "yesterday", "today", or "tomorrow" where appropriate # noqa: E501
    TIME = "{time}"  # %H:%M %p in 12-hour format, or %H:%M in 24-hour format based on client settings # noqa: E501
    TIME_SECS = "{time_secs}"  # %H:%M:%S [%p]


class SlackDatetime:
    def __init__(self, timestamp: datetime.datetime, format_string: str):
        self.value = (
            f"<!date^{int(timestamp.timestamp())}^{format_string}| {timestamp}>"
        )

    def __repr__(self):
        return self.value


class DateShortPretty(SlackDatetime):
    formatter = f"{DatetimeFormats.DATE_SHORT_PRETTY.value}"

    def __init__(self, timestamp: datetime.datetime):
        super().__init__(timestamp, self.formatter)


class DateTimeShortPretty(SlackDatetime):
    formatter = (
        f"{DatetimeFormats.DATE_SHORT_PRETTY.value}, {DatetimeFormats.TIME.value}"
    )

    def __init__(self, timestamp: datetime.datetime):
        super().__init__(timestamp, self.formatter)
