import argparse
import os

from rawformer               import ROOT_OUTDIR, train
from rawformer.presets       import GEN_PRESETS, BH_PRESETS
from rawformer.utils.parsers import add_preset_name_parser

def parse_cmdargs():
    parser = argparse.ArgumentParser(
        description = 'Train Image2Image I2I model'
    )

    add_preset_name_parser(parser, 'gen',  GEN_PRESETS, 'rawformer')
    add_preset_name_parser(parser, 'head', BH_PRESETS,  'bn', 'batch head')

    parser.add_argument(
        '--no-pretrain', dest = 'no_pretrain', action = 'store_true',
        help = 'disable uasge of the pre-trained generator'
    )

    parser.add_argument(
        '--lambda-gp', dest = 'lambda_gp', type = float,
        default = 0.01, help = 'magnitude of the gradient penalty'
    )

    parser.add_argument(
        '--lambda-cycle', dest = 'lambda_cyc', type = float,
        default = 10.0, help = 'magnitude of the cycle-consisntecy loss'
    )

    parser.add_argument(
        '--lr-gen', dest = 'lr_gen', type = float,
        default = 5e-5, help = 'learning rate of the generator'
    )

    return parser.parse_args()

def get_transfer_preset(cmdargs):
    if cmdargs.no_pretrain:
        return None

    base_model = (
        'image2image/'
        'model_m(autoencoder)_d(None)'
        f"_g({GEN_PRESETS[cmdargs.gen]['model']})_pretrain-{cmdargs.gen}"
    )

    return {
        'base_model' : base_model,
        'transfer_map'  : {
            'gen_ab' : 'encoder',
            'gen_ba' : 'encoder',
        },
        'strict'        : True,
        'allow_partial' : False,
        'fuzzy'         : None,
    }

cmdargs   = parse_cmdargs()
args_dict = {
    'batch_size' : 1,
    'data' : {
        'datasets' : [
            {
                'dataset' : {
                    'name'   : 'cyclegan',
                    'domain' : domain,
                    'path'   : 'image2image',
                },
                'shape'           : (3, 256, 256),
                'transform_train' : [
                    { 'name' : 'resize',      'size' : 286, },
                    { 'name' : 'random-crop', 'size' : 256, },
                    'random-flip-horizontal',
                ],
                'transform_test' : None,
            } for domain in [ 'a', 'b' ]
        ],
        'merge_type' : 'unpaired',
        'workers'    : 1,
    },
    'epochs'      : 5, # 500 epochs
    'discriminator' : {
        'model'      : 'basic',
        'model_args' : { 'shrink_output' : False, },
        'optimizer'  : {
            'name'  : 'Adam',
            'lr'    : 1e-4,
            'betas' : (0.5, 0.99),
        },
        'weight_init' : {
            'name'      : 'normal',
            'init_gain' : 0.02,
        },
        'spectr_norm' : True,
    },
    'generator' : {
        **GEN_PRESETS[cmdargs.gen],
        'optimizer'  : {
            'name'  : 'Adam',
            'lr'    : cmdargs.lr_gen,
            'betas' : (0.5, 0.99),
        },
        'weight_init' : {
            'name'      : 'normal',
            'init_gain' : 0.02,
        },
    },
    'model' : 'rawformer',
    'model_args' : {
        'lambda_a'        : cmdargs.lambda_cyc,
        'lambda_b'        : cmdargs.lambda_cyc,
        'lambda_idt'      : 0.5,
        'avg_momentum'    : 0.9999,
        'head_queue_size' : 3,
        'head_config'     : {
            'name'            : BH_PRESETS[cmdargs.head],
            'input_features'  : 512,
            'output_features' : 1,
            'activ'           : 'leakyrelu',
        },
    },
    'gradient_penalty' : {
        'center'    : 0,
        'lambda_gp' : cmdargs.lambda_gp,
        'mix_type'  : 'real-fake',
        'reduction' : 'mean',
    },
    'scheduler'       : None,
    'loss'            : 'lsgan',
    'steps_per_epoch' : 2000,
    'transfer'        : get_transfer_preset(cmdargs),
# args
    'label'  : (
        f'{cmdargs.gen}-{cmdargs.head}_({cmdargs.no_pretrain}'
        f':{cmdargs.lambda_cyc}:{cmdargs.lambda_gp}:{cmdargs.lr_gen})'
    ),
    'outdir' : os.path.join(ROOT_OUTDIR, 'image2image', 'image2image'),
    'log_level'  : 'DEBUG',
    'checkpoint' : 50,
}

train(args_dict)

