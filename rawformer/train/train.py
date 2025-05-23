from itertools import islice
import tqdm

from rawformer.config      import Args
from rawformer.data        import construct_data_loaders
from rawformer.torch.funcs import get_torch_device_smart, seed_everything
from rawformer.cgan        import construct_model
from rawformer.utils.log   import setup_logging

from .metrics   import LossMetrics
from .callbacks import TrainingHistory
from .transfer  import transfer
import torch
import torch
import torchvision
import imageio
import os


def save_grid(images: torch.Tensor, gt: torch.Tensor, savedir):
    vis = torch.cat([images, gt], dim = 0)
    grid = torchvision.utils.make_grid(vis, nrow=images.shape[0], normalize=True).permute(1, 2, 0).cpu().numpy()
    grid = (grid * 255).astype('uint8')
    imageio.v3.imwrite(os.path.join(savedir, 'sample.png'), grid)


def training_epoch(it_train, model, title, steps_per_epoch, savedir):
    model.train()

    steps = len(it_train)
    if steps_per_epoch is not None:
        steps = min(steps, steps_per_epoch)

    progbar = tqdm.tqdm(desc = title, total = steps, dynamic_ncols = True)
    metrics = LossMetrics()

    for batch in islice(it_train, steps):
        model.set_input(batch)
        model.optimization_step()

        metrics.update(model.get_current_losses())

        progbar.set_postfix(metrics.values, refresh = False)
        progbar.update()

    save_grid(model.images.reco_a, model.images.real_a, savedir)
    progbar.close()
    return metrics

def try_continue_training(args, model):
    history = TrainingHistory(args.savedir)

    start_epoch = model.find_last_checkpoint_epoch()
    model.load(start_epoch)

    if start_epoch > 0:
        history.load()

    start_epoch = max(start_epoch, 0)

    return (start_epoch, history)

def train(args_dict):
    args = Args.from_args_dict(**args_dict)

    setup_logging(args.log_level)
    seed_everything(args.config.seed)

    device   = get_torch_device_smart()
    it_train = construct_data_loaders(
        args.config.data, args.config.batch_size, split = 'train'
    )

    print("Starting training...")
    print(args.config.to_json(indent = 4))

    model = construct_model(
        args.savedir, args.config, is_train = True, device = device
    )
    start_epoch, history = try_continue_training(args, model)

    if (start_epoch == 0) and (args.transfer is not None):
        transfer(model, args.transfer)

    for epoch in range(start_epoch + 1, args.epochs + 1):
        title   = 'Epoch %d / %d' % (epoch, args.epochs)
        metrics = training_epoch(
            it_train, model, title, args.config.steps_per_epoch, args.savedir
        )

        history.end_epoch(epoch, metrics)
        model.end_epoch(epoch)

        if epoch % args.checkpoint == 0:
            model.save(epoch)

    model.save(epoch = None)
