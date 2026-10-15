"""
U-Net Generator Architecture for Anime2Sketch.
Ported from Anime2Sketch (Xiaoyu Xiang et al. / Purdue University).
Supports both standard and improved upsampled generators.
"""

import functools

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    nn = object
    F = None


if HAS_TORCH:
    class UnetGenerator(nn.Module):
        """Create a Unet-based generator for sketch extraction."""

        def __init__(self, input_nc=3, output_nc=1, num_downs=8, ngf=64, norm_layer=nn.BatchNorm2d, use_dropout=False):
            super(UnetGenerator, self).__init__()
            unet_block = UnetSkipConnectionBlock(ngf * 8, ngf * 8, input_nc=None, submodule=None, norm_layer=norm_layer, innermost=True)
            for _ in range(num_downs - 5):
                unet_block = UnetSkipConnectionBlock(ngf * 8, ngf * 8, input_nc=None, submodule=unet_block, norm_layer=norm_layer, use_dropout=use_dropout)
            unet_block = UnetSkipConnectionBlock(ngf * 4, ngf * 8, input_nc=None, submodule=unet_block, norm_layer=norm_layer)
            unet_block = UnetSkipConnectionBlock(ngf * 2, ngf * 4, input_nc=None, submodule=unet_block, norm_layer=norm_layer)
            unet_block = UnetSkipConnectionBlock(ngf, ngf * 2, input_nc=None, submodule=unet_block, norm_layer=norm_layer)
            self.model = UnetSkipConnectionBlock(output_nc, ngf, input_nc=input_nc, submodule=unet_block, outermost=True, norm_layer=norm_layer)

        def forward(self, input_tensor):
            return self.model(input_tensor)

    class UnetSkipConnectionBlock(nn.Module):
        """Defines the Unet submodule with skip connection."""

        def __init__(self, outer_nc, inner_nc, input_nc=None,
                     submodule=None, outermost=False, innermost=False, norm_layer=nn.BatchNorm2d, use_dropout=False):
            super(UnetSkipConnectionBlock, self).__init__()
            self.outermost = outermost
            if isinstance(norm_layer, functools.partial):
                use_bias = norm_layer.func == nn.InstanceNorm2d
            else:
                use_bias = norm_layer == nn.InstanceNorm2d
            if input_nc is None:
                input_nc = outer_nc
            downconv = nn.Conv2d(input_nc, inner_nc, kernel_size=4,
                                 stride=2, padding=1, bias=use_bias)
            downrelu = nn.LeakyReLU(0.2, True)
            downnorm = norm_layer(inner_nc)
            uprelu = nn.ReLU(True)
            upnorm = norm_layer(outer_nc)

            if outermost:
                upconv = nn.ConvTranspose2d(inner_nc * 2, outer_nc,
                                            kernel_size=4, stride=2,
                                            padding=1)
                down = [downconv]
                up = [uprelu, upconv, nn.Tanh()]
                model = down + [submodule] + up
            elif innermost:
                upconv = nn.ConvTranspose2d(inner_nc, outer_nc,
                                            kernel_size=4, stride=2,
                                            padding=1, bias=use_bias)
                down = [downrelu, downconv]
                up = [uprelu, upconv, upnorm]
                model = down + up
            else:
                upconv = nn.ConvTranspose2d(inner_nc * 2, outer_nc,
                                            kernel_size=4, stride=2,
                                            padding=1, bias=use_bias)
                down = [downrelu, downconv, downnorm]
                up = [uprelu, upconv, upnorm]
                if use_dropout:
                    model = down + [submodule] + up + [nn.Dropout(0.5)]
                else:
                    model = down + [submodule] + up

            self.model = nn.Sequential(*model)

        def forward(self, x):
            if self.outermost:
                return self.model(x)
            else:
                return torch.cat([x, self.model(x)], 1)

    class Smooth(nn.Module):
        def __init__(self):
            super().__init__()
            kernel = [
                [1, 2, 1],
                [2, 4, 2],
                [1, 2, 1]
            ]
            kernel = torch.tensor([[kernel]], dtype=torch.float)
            kernel /= kernel.sum()
            self.register_buffer('kernel', kernel)
            self.pad = nn.ReplicationPad2d(1)

        def forward(self, x):
            b, c, h, w = x.shape
            x = x.view(-1, 1, h, w)
            x = self.pad(x)
            x = F.conv2d(x, self.kernel)
            return x.view(b, c, h, w)

    class Upsample(nn.Module):
        def __init__(self, inc, outc, scale_factor=2):
            super().__init__()
            self.scale_factor = scale_factor
            self.up = nn.Upsample(scale_factor=scale_factor, mode='bilinear')
            self.smooth = Smooth()
            self.conv = nn.Conv2d(inc, outc, kernel_size=3, stride=1, padding=1)
            self.mlp = nn.Sequential(
                nn.Conv2d(outc, 4 * outc, kernel_size=1, stride=1, padding=0),
                nn.GELU(),
                nn.Conv2d(4 * outc, outc, kernel_size=1, stride=1, padding=0),
            )

        def forward(self, x):
            x = self.smooth(self.up(x))
            x = self.conv(x)
            x = self.mlp(x) + x
            return x

    def create_sketch_model(weights_path=None, model_type='default', device='cpu'):
        norm_layer = functools.partial(nn.InstanceNorm2d, affine=False, track_running_stats=False)
        net = UnetGenerator(3, 1, 8, 64, norm_layer=norm_layer, use_dropout=False)

        if weights_path and torch and torch.os.path.exists(weights_path):
            ckpt = torch.load(weights_path, map_location=torch.device(device))
            for key in list(ckpt.keys()):
                if 'module.' in key:
                    ckpt[key.replace('module.', '')] = ckpt[key]
                    del ckpt[key]
            net.load_state_dict(ckpt)

        net.to(device)
        net.eval()
        return net
else:
    class UnetGenerator:
        pass
    class UnetSkipConnectionBlock:
        pass
    class Smooth:
        pass
    class Upsample:
        pass
    def create_sketch_model(*args, **kwargs):
        raise RuntimeError("PyTorch is not installed in the current environment.")
