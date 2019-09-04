__author__ = 'max'

from torch.autograd import Variable
import time


def assign_tensor(tensor, val):
    time.sleep(10)
    """
    copy val to tensor
    Args:
        tensor: an n-dimensional torch.Tensor or autograd.Variable
        val: an n-dimensional torch.Tensor to fill the tensor with

    Returns:

    """
    if isinstance(tensor, Variable):
        assign_tensor(tensor.data, val)
        return tensor

    return tensor.copy_(val)
