# Copyright 2020 - 2021 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
A collection of dictionary-based wrappers around the "vanilla" transforms for IO functions
defined in :py:class:`monai.transforms.io.array`.

Class names are ended with 'd' to denote dictionary-based transforms.
"""

from typing import Callable, Optional, Union

import numpy as np

from monai.config import KeysCollection
from monai.data.image_reader import ImageReader
from monai.transforms.compose import MapTransform
from monai.transforms.io.array import LoadImage, LoadNifti, LoadNumpy, LoadPNG

__all__ = ["LoadImaged", "LoadDatad", "LoadNiftid", "LoadPNGd", "LoadNumpyd"]


class LoadImaged(MapTransform):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.LoadImage`,
    must load image and metadata together. If loading a list of files in one key,
    stack them together and add a new dimension as the first dimension, and use the
    meta data of the first image to represent the stacked result. Note that the affine
    transform of all the stacked images should be same. The output metadata field will
    be created as ``key_{meta_key_postfix}``.

    It can automatically choose readers based on the supported suffixes and in below order:
    - User specified reader at runtime when call this loader.
    - Registered readers from the latest to the first in list.
    - Default readers: (nii, nii.gz -> NibabelReader), (png, jpg, bmp -> PILReader),
    (npz, npy -> NumpyReader), (others -> ITKReader).

    """

    def __init__(
        self,
        keys: KeysCollection,
        reader: Optional[Union[ImageReader, str]] = None,
        dtype: Optional[np.dtype] = np.float32,
        meta_key_postfix: str = "meta_dict",
        overwriting: bool = False,
        *args,
        **kwargs,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            reader: register reader to load image file and meta data, if None, still can register readers
                at runtime or use the default readers. If a string of reader name provided, will construct
                a reader object with the `*args` and `**kwargs` parameters, supported reader name: "NibabelReader",
                "PILReader", "ITKReader", "NumpyReader"
            dtype: if not None convert the loaded image data to this data type.
            meta_key_postfix: use `key_{postfix}` to store the metadata of the nifti image,
                default is `meta_dict`. The meta data is a dictionary object.
                For example, load nifti file for `image`, store the metadata into `image_meta_dict`.
            overwriting: whether allow to overwrite existing meta data of same key.
                default is False, which will raise exception if encountering existing key.
            args: additional parameters for reader if providing a reader name.
            kwargs: additional parameters for reader if providing a reader name.
        """
        super().__init__(keys)
        self._loader = LoadImage(reader, False, dtype, *args, **kwargs)
        if not isinstance(meta_key_postfix, str):
            raise TypeError(f"meta_key_postfix must be a str but is {type(meta_key_postfix).__name__}.")
        self.meta_key_postfix = meta_key_postfix
        self.overwriting = overwriting

    def register(self, reader: ImageReader):
        self._loader.register(reader)

    def __call__(self, data, reader: Optional[ImageReader] = None):
        """
        Raises:
            KeyError: When not ``self.overwriting`` and key already exists in ``data``.

        """
        d = dict(data)
        for key in self.keys:
            data = self._loader(d[key], reader)
            if not isinstance(data, (tuple, list)):
                raise ValueError("loader must return a tuple or list.")
            d[key] = data[0]
            if not isinstance(data[1], dict):
                raise ValueError("metadata must be a dict.")
            key_to_add = f"{key}_{self.meta_key_postfix}"
            if key_to_add in d and not self.overwriting:
                raise KeyError(f"Meta data with key {key_to_add} already exists and overwriting=False.")
            d[key_to_add] = data[1]
        return d


class LoadDatad(MapTransform):
    """
    Base class for dictionary-based wrapper of IO loader transforms.
    It must load image and metadata together. If loading a list of files in one key,
    stack them together and add a new dimension as the first dimension, and use the
    meta data of the first image to represent the stacked result. Note that the affine
    transform of all the stacked images should be same. The output metadata field will
    be created as ``key_{meta_key_postfix}``.
    """

    def __init__(
        self,
        keys: KeysCollection,
        loader: Callable,
        meta_key_postfix: str = "meta_dict",
        overwriting: bool = False,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            loader: callable function to load data from expected source.
                typically, it's array level transform, for example: `LoadNifti`,
                `LoadPNG` and `LoadNumpy`, etc.
            meta_key_postfix: use `key_{postfix}` to store the metadata of the loaded data,
                default is `meta_dict`. The meta data is a dictionary object.
                For example, load Nifti file for `image`, store the metadata into `image_meta_dict`.
            overwriting: whether allow to overwrite existing meta data of same key.
                default is False, which will raise exception if encountering existing key.

        Raises:
            TypeError: When ``loader`` is not ``callable``.
            TypeError: When ``meta_key_postfix`` is not a ``str``.

        """
        super().__init__(keys)
        if not callable(loader):
            raise TypeError(f"loader must be callable but is {type(loader).__name__}.")
        self.loader = loader
        if not isinstance(meta_key_postfix, str):
            raise TypeError(f"meta_key_postfix must be a str but is {type(meta_key_postfix).__name__}.")
        self.meta_key_postfix = meta_key_postfix
        self.overwriting = overwriting

    def __call__(self, data):
        """
        Raises:
            KeyError: When not ``self.overwriting`` and key already exists in ``data``.

        """
        d = dict(data)
        for key in self.keys:
            data = self.loader(d[key])
            assert isinstance(data, (tuple, list)), "loader must return a tuple or list."
            d[key] = data[0]
            assert isinstance(data[1], dict), "metadata must be a dict."
            key_to_add = f"{key}_{self.meta_key_postfix}"
            if key_to_add in d and not self.overwriting:
                raise KeyError(f"Meta data with key {key_to_add} already exists and overwriting=False.")
            d[key_to_add] = data[1]
        return d


class LoadNiftid(LoadDatad):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.LoadNifti`,
    must load image and metadata together. If loading a list of files in one key,
    stack them together and add a new dimension as the first dimension, and use the
    meta data of the first image to represent the stacked result. Note that the affine
    transform of all the stacked images should be same. The output metadata field will
    be created as ``key_{meta_key_postfix}``.
    """

    def __init__(
        self,
        keys: KeysCollection,
        as_closest_canonical: bool = False,
        dtype: Optional[np.dtype] = np.float32,
        meta_key_postfix: str = "meta_dict",
        overwriting: bool = False,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            as_closest_canonical: if True, load the image as closest to canonical axis format.
            dtype: if not None convert the loaded image data to this data type.
            meta_key_postfix: use `key_{postfix}` to store the metadata of the nifti image,
                default is `meta_dict`. The meta data is a dictionary object.
                For example, load nifti file for `image`, store the metadata into `image_meta_dict`.
            overwriting: whether allow to overwrite existing meta data of same key.
                default is False, which will raise exception if encountering existing key.
        """
        loader = LoadNifti(as_closest_canonical, False, dtype)
        super().__init__(keys, loader, meta_key_postfix, overwriting)


class LoadPNGd(LoadDatad):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.LoadPNG`.
    """

    def __init__(
        self,
        keys: KeysCollection,
        dtype: Optional[np.dtype] = np.float32,
        meta_key_postfix: str = "meta_dict",
        overwriting: bool = False,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            dtype: if not None convert the loaded image data to this data type.
            meta_key_postfix: use `key_{postfix}` to store the metadata of the PNG image,
                default is `meta_dict`. The meta data is a dictionary object.
                For example, load PNG file for `image`, store the metadata into `image_meta_dict`.
            overwriting: whether allow to overwrite existing meta data of same key.
                default is False, which will raise exception if encountering existing key.
        """
        loader = LoadPNG(False, dtype)
        super().__init__(keys, loader, meta_key_postfix, overwriting)


class LoadNumpyd(LoadDatad):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.LoadNumpy`.
    """

    def __init__(
        self,
        keys: KeysCollection,
        dtype: Optional[np.dtype] = np.float32,
        npz_keys: Optional[KeysCollection] = None,
        meta_key_postfix: str = "meta_dict",
        overwriting: bool = False,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            dtype: if not None convert the loaded data to this data type.
            npz_keys: if loading npz file, only load the specified keys, if None, load all the items.
                stack the loaded items together to construct a new first dimension.
            meta_key_postfix: use `key_{postfix}` to store the metadata of the Numpy data,
                default is `meta_dict`. The meta data is a dictionary object.
                For example, load Numpy file for `mask`, store the metadata into `mask_meta_dict`.
            overwriting: whether allow to overwrite existing meta data of same key.
                default is False, which will raise exception if encountering existing key.
        """
        loader = LoadNumpy(data_only=False, dtype=dtype, npz_keys=npz_keys)
        super().__init__(keys, loader, meta_key_postfix, overwriting)


LoadImageD = LoadImageDict = LoadImaged
LoadNiftiD = LoadNiftiDict = LoadNiftid
LoadPNGD = LoadPNGDict = LoadPNGd
LoadNumpyD = LoadNumpyDict = LoadNumpyd
