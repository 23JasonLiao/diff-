"""Minimal patch instructions for your Network.py / networkold.py.

Goal: train TWO models that differ only by self-attention:
    A: use_attention=True  (current architecture)
    B: use_attention=False (CNN-only ablation)

Do NOT merely set attn_resolutions=[] because your deepest decoder in0 block
is hard-coded with attention=True in the current Network.py.
"""

# 1) Add an argument to UNet.__init__:
#
#   use_attention = True,
#
# and store it if desired:
#   self.use_attention = use_attention

# 2) Encoder block creation: replace
#
#   attention=(resx in attn_resolutions)
#
# with
#
#   attention=(use_attention and (resx in attn_resolutions))

# 3) Deepest decoder block: replace
#
#   self.dec[f'{resx}x{resy}_in0'] = UNetBlock(
#       in_channels=cout, out_channels=cout, attention=True, **block_kwargs)
#
# with
#
#   self.dec[f'{resx}x{resy}_in0'] = UNetBlock(
#       in_channels=cout, out_channels=cout,
#       attention=use_attention, **block_kwargs)

# 4) Decoder blocks: replace
#
#   attention=(resx in attn_resolutions)
#
# with
#
#   attention=(use_attention and (resx in attn_resolutions))

# 5) Training construction:
#
#   network = networkold.EDMPrecond(
#       dataset_train.img_resolution,
#       model_in_channels,
#       model_out_channels,
#       label_dim=2,
#       model_channels=64,           # MUST match your actual checkpoint/config
#       channel_mult=[1,2,3,4],
#       num_blocks=2,
#       dropout=0.10,
#       use_attention=args.use_attention,
#   )
#
# and add CLI flags, e.g.:
#
#   parser.add_argument('--use-attention', dest='use_attention', action='store_true')
#   parser.add_argument('--no-attention', dest='use_attention', action='store_false')
#   parser.set_defaults(use_attention=True)

# IMPORTANT:
# Train the OFF model from scratch. A checkpoint trained WITH attention cannot
# be loaded strictly into the OFF architecture because qkv/proj parameters no
# longer exist. Likewise, simply zeroing attention at inference is a different
# experiment (intervention on a trained model), not a fair architecture ablation.
