from common import *
import random
from model_gen.mg_common import *
import config
from pyspark.mllib.regression import LabeledPoint


FEATURE_FAM = 'ext-mem-rw-dump'


class UploadSearch:
    def __init__(self, extractor_pack=None, feature_family=None, sample=None):
        self._extractor_pack = extractor_pack
        self._feature_family = feature_family
        self._sample = sample

    @staticmethod
    def s():
        return Search(using=get_elastic(), index=config.REDIS_CONF_UPLOADS[0], doc_type=config.REDIS_CONF_UPLOADS[1])

    def search(self):
        ret = UploadSearch.s()
        if self._extractor_pack is not None:
            ret = ret.filter('match', extractor_pack=self._extractor_pack)
        if self._feature_family is not None:
            ret = ret.filter('match', feature_family=self._feature_family)
        if self._sample is not None:
            ret = ret.filter('match', sample=self._sample)

        return ret.execute()


class SampleSearch:
    def __init__(self, label=None, arch=None, source=None, sample=None):
        self._label = label
        self._arch = arch
        self._source = source
        self._sample = sample

    @staticmethod
    def s():
        return Search(using=get_elastic(), index=config.REDIS_CONF_SAMPLES[0], doc_type=config.REDIS_CONF_SAMPLES[1])

    def search(self):
        ret = SampleSearch.s()
        if self._label is not None:
            ret = ret.filter('match', label=self._label)
        if self._arch is not None:
            ret = ret.filter('match', arch=self._arch)
        if self._source is not None:
            ret = ret.filter('match', source=self._source)
        if self._sample is not None:
            ret = ret.filter('match', sample=self._sample)

        return ret.execute()


def get_labelled_sample_set(_feature_fam, _label, count, exclude=[]):
    ret = []
    labelled_samples = SampleSearch(label=_label).search()

    for _sample in labelled_samples:
        for result in UploadSearch(extractor_pack='pack-1', sample=_sample).search():
            ret.append(result)

    if len(ret) >= count:
        return random.sample(ret, count)
    else:
        return []


class ModelBuilder:
    @staticmethod
    def get_feature_labeled_points(feature_json, label):
        ret = []

        for feature_set in feature_json['feature_sets']:
            feature_data = feature_json['feature_sets'][feature_set]['feature_data']
            ret.append((feature_set, LabeledPoint(label, [float(f) for f in feature_data])))

        return ret


class SampleLabelPredicter:
    MALWARE = 1.0
    BENIGN = 0.0

    def __init__(self, detonation_sample, pcount_min=5, pcount_perc=None):
        self.sample = detonation_sample
        self.sample_json = detonation_sample.get_metadata()

        self.pcount_min = pcount_min
        self.pcount_perc = pcount_perc

    def get_scan_data(self):
        if 'vti' in self.sample_json:
            return self.sample_json['vti']['scans']
        elif 'existing_metadata' in self.sample_json:
            return self.sample_json['existing_metadata']['scans']
        else:
            raise Exception('no AV data!')

    def vti_predict_label(self):
        scan_data = self.get_scan_data()
        detected = 0
        for i in scan_data:
            if scan_data[i]['detected'] is True:
                detected += 1

        if self.pcount_perc is not None:
            if (detected / float(len(scan_data)) * 100) > self.pcount_perc:
                return SampleLabelPredicter.MALWARE
            else:
                return SampleLabelPredicter.BENIGN
        else:
            if detected > self.pcount_min:
                return SampleLabelPredicter.MALWARE
            else:
                return SampleLabelPredicter.BENIGN

    def get_explicit_label(self):
        if 'label' in self.sample_json:
            return self.sample_json['label']
        else:
            return None

    def get_label(self):
        if self.get_explicit_label() is not None:
            return self.get_explicit_label()
        else:
            return self.vti_predict_label()

if __name__ == '__main__':
    #generate_model(FEATURE_FAM)

    with open('features/615cc5670435e88acb614c467d6dc9b09637f917f02f3b14cd8460d1ac6058ec/2/ext-mem-rw-dump-0.0.1.json') as fd:
        j = json.loads(fd.read())
    print ModelBuilder.get_feature_labeled_points(j, 1.0)

    print SampleLabelPredicter(DetonationSample('ff808d0a12676bfac88fd26f955154f8884f2bb7c534b9936510fd6296c543e8')).get_label()