class NurError(Exception):
    pass


class EvalError(NurError):
    pass


class RepositoryDeletedError(NurError):
    pass
