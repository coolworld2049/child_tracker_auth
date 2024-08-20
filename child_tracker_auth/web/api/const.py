from datetime import date

from dateutil.relativedelta import relativedelta

date_from_default: date = date.today() - relativedelta(months=6)
date_to_default: date = date.today()
