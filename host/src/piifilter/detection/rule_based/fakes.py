from piifilter.languages import LanguageConfig


class FakeAssigner:
    def __init__(self, lang_config: LanguageConfig):
        self.pools = lang_config.fake_pools
        self._by_original: dict[tuple[str, str], str] = {}
        self._used: dict[str, int] = {}

    def get(self, category: str, original: str) -> str:
        key = (category, original)
        if key in self._by_original:
            return self._by_original[key]
        n = self._used.get(category, 0)
        self._used[category] = n + 1
        pool = self.pools.get(category, [])
        if n < len(pool):
            fake = pool[n]
        else:
            fake = f"[{category}_{n + 1}]"
        self._by_original[key] = fake
        return fake
