from .base_adapter import BaseAdapter
from .aa_adapter import AAAdapter
from .trt_adapter import TRTAdapter
from .iha_adapter import IHAAdapter
from .dha_adapter import DHAAdapter
from .ntv_adapter import NTVAdapter
from .haberturk_adapter import HaberturkAdapter
from .milliyet_adapter import MilliyetAdapter
from .hurriyet_adapter import HurriyetAdapter
from .ahaber_adapter import AHaberAdapter
from .yenisafak_adapter import YeniSafakAdapter
from .sabah_adapter import SabahAdapter
from .turkiyegazetesi_adapter import TurkiyeGazetesiAdapter
from .sozcu_adapter import SozcuAdapter
from .cumhuriyet_adapter import CumhuriyetAdapter
from .halktv_adapter import HalkTVAdapter
from .t24_adapter import T24Adapter
from .birgun_adapter import BirgunAdapter

ALL_ADAPTER_CLASSES = [
    AAAdapter,
    TRTAdapter,
    IHAAdapter,
    DHAAdapter,
    NTVAdapter,
    HaberturkAdapter,
    MilliyetAdapter,
    HurriyetAdapter,
    AHaberAdapter,
    YeniSafakAdapter,
    SabahAdapter,
    TurkiyeGazetesiAdapter,
    SozcuAdapter,
    CumhuriyetAdapter,
    HalkTVAdapter,
    T24Adapter,
    BirgunAdapter
]
