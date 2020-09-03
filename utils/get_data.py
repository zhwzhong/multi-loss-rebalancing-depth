from utils.data import loadZipToMem, ToTensor_with_RandomZoom, depthDatasetMemoryTrain
from torchvision import transforms
from torch.utils.data import DataLoader
import numpy as np
from PIL import Image
import collections
import torch
from utils.transform import *

try:
    import accimage
except ImportError:
    accimage =None

def getTrainingData(batch_size, train_dataset_path, train_dataset_csv_list):
    data_temp, train_temp = loadZipToMem(train_dataset_path, train_dataset_csv_list)
    data = data_temp.copy()
    train = train_temp

    __imagenet_pca = {
        'eigval': torch.Tensor([0.2175, 0.0188, 0.0045]),
        'eigvec': torch.Tensor([
            [-0.5675, 0.7192, 0.4009],
            [-0.5808, -0.0045, -0.8140],
            [-0.5836, -0.6948, 0.4203],
        ])
    }
    __imagenet_stats = {'mean': [0.485, 0.456, 0.406],
                        'std': [0.229, 0.224, 0.225]}

    transformed_training = transforms.Compose([
        Scale(288),
        RandomHorizontalFlip(),
        RandomRotate(5),
        #RandomChannelSwap(0.5),
        ToTensor_with_RandomZoom(ratio=1.00),
        Lighting(0.1, __imagenet_pca['eigval'], __imagenet_pca['eigvec']),
        ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, ),
        Normalize(__imagenet_stats['mean'],
                  __imagenet_stats['std'])
        ])

    transformed_training = depthDatasetMemoryTrain(data, train, transform=transformed_training)

    return DataLoader(transformed_training, batch_size, shuffle=True), len(train)

def getTestingData(batch_size, test_dataset_path, test_dataset_csv_list):
    data_temp, test_temp = loadZipToMem(test_dataset_path, test_dataset_csv_list)
    data = data_temp.copy()
    test = test_temp

    __imagenet_stats = {'mean': [0.485, 0.456, 0.406],
                        'std': [0.229, 0.224, 0.225]}

    autransformed_testing = transforms.Compose([
        Scale(480),
        ToTensor_with_RandomZoom(ratio=1.00),
        Normalize(__imagenet_stats['mean'],
                  __imagenet_stats['std'])
    ])

    transformed_testing = depthDatasetMemoryTrain(data, test, transform=autransformed_testing)

    return DataLoader(transformed_testing, batch_size, shuffle=False), len(test)

def _is_pil_image(img):
    if accimage is not None:
        return isinstance(img, (Image.Image, accimage.Image))
    else:
        return isinstance(img, Image.Image)


def _is_numpy_image(img):
    return isinstance(img, np.ndarray) and (img.ndim in {2, 3})

class Scale(object):
    """ Rescales the inputs and target arrays to the given 'size'.
    'size' will be the size of the smaller edge.
    For example, if height > width, then image will be
    rescaled to (size * height / width, size)
    size: size of the smaller edge
    interpolation order: Default: 2 (bilinear)
    """

    def __init__(self, size):
        self.size = size

    def __call__(self, sample):
        image, depth = sample['image'], sample['depth']

        image = self.changeScale(image, self.size)
        depth = self.changeScale(depth, self.size, Image.NEAREST)

        return {'image': image, 'depth': depth}

    def changeScale(self, img, size, interpolation=Image.BILINEAR):

        if not _is_pil_image(img):
            raise TypeError(
                'img should be PIL Image. Got {}'.format(type(img)))
        if not (isinstance(size, int) or (isinstance(size, collections.Iterable) and len(size) == 2)):
            raise TypeError('Got inappropriate size arg: {}'.format(size))

        if isinstance(size, int):
            w, h = img.size
            if (w <= h and w == size) or (h <= w and h == size):
                return img
            if w < h:
                ow = size
                oh = int(size * h / w)
                return img.resize((ow, oh), interpolation)
            else:
                oh = size
                ow = int(size * w / h)
                return img.resize((ow, oh), interpolation)
        else:
            return img.resize(size[::-1], interpolation)

class Normalize(object):
    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def __call__(self, sample):
        """
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.
        Returns:
            Tensor: Normalized image.
        """
        image, depth = sample['image'], sample['depth']

        image = self.normalize(image, self.mean, self.std)

        return {'image': image, 'depth': depth}

    def normalize(self, tensor, mean, std):
        """Normalize a tensor image with mean and standard deviation.
        See ``Normalize`` for more details.
        Args:
            tensor (Tensor): Tensor image of size (C, H, W) to be normalized.
            mean (sequence): Sequence of means for R, G, B channels respecitvely.
            std (sequence): Sequence of standard deviations for R, G, B channels
                respecitvely.
        Returns:
            Tensor: Normalized image.
        """

        # TODO: make efficient
        for t, m, s in zip(tensor, mean, std):
            t.sub_(m).div_(s)
        return tensor