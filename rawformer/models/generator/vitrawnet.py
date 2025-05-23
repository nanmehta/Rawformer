# pylint: disable=too-many-arguments
# pylint: disable=too-many-instance-attributes

from torch import nn

from rawformer.torch.layers.transformer import ExtendedPixelwiseViT
#from rawformer.torch.layers.rawnet_basic      import RawNet
from rawformer.torch.layers.rawnet      import RawNet
from rawformer.torch.select             import get_activ_layer

class ViTRawNetGenerator(nn.Module):

    def __init__(
        self, features, n_heads, n_blocks, ffn_features, embed_features,
        activ, norm, input_shape, output_shape, modnet_features_list,
        modnet_activ,
        modnet_norm       = None,
        modnet_downsample = 'conv',
        modnet_upsample   = 'upsample-conv',
        modnet_rezero     = False,
        modnet_demod      = True,
        rezero            = True,
        activ_output      = None,
        style_rezero      = True,
        style_bias        = True,
        n_ext             = 1,
        rawnet_num_heads  = 1,
        rawnet_token_size = 4,
        **kwargs
    ):
        # pylint: disable = too-many-locals
        super().__init__(**kwargs)

        assert input_shape == output_shape
        image_shape = input_shape

        self.image_shape = image_shape

        mod_features = features * n_ext

        self.net = RawNet(
            modnet_features_list, modnet_activ, modnet_norm, image_shape,
            modnet_downsample, modnet_upsample, mod_features, modnet_rezero,
            modnet_demod, style_rezero, style_bias, return_mod = False,
            num_heads=rawnet_num_heads, token_size=rawnet_token_size,
        )

        bottleneck = ExtendedPixelwiseViT(
            features, n_heads, n_blocks, ffn_features, embed_features,
            activ, norm,
            image_shape = self.net.get_inner_shape(),
            rezero      = rezero,
            n_ext       = n_ext,
        )

        self.net.set_bottleneck(bottleneck)

        self.output = get_activ_layer(activ_output)

    def forward(self, x):
        # x : (N, C, H, W)
        result = self.net(x)
        return self.output(result)

