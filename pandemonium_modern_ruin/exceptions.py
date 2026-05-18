class PandemoniumError(Exception):
    pass


class InsufficientResources(PandemoniumError):
    pass


class InvalidTarget(PandemoniumError):
    pass


class AbilityNotFound(PandemoniumError):
    pass


class SaveGameError(PandemoniumError):
    pass
