import torch
from torchvision import transforms
from torch.autograd import Variable
from dataset import DatasetFromFolder
from model import Generator, Discriminator
import utils
import argparse
import os, itertools
from logger import Logger
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--dataset', required=False, default='sketch-photo', help='input dataset')
parser.add_argument('--batch_size', type=int, default=16, help='train batch size')
parser.add_argument('--ngf', type=int, default=64)
parser.add_argument('--ndf', type=int, default=64)
parser.add_argument('--input_size', type=int, default=256, help='input size')
parser.add_argument('--num_channel', type=int, default=3, help='number of channels for input image')
parser.add_argument('--fliplr', type=bool, default=True, help='random fliplr True of False')
parser.add_argument('--num_epochs', type=int, default=45, help='number of train epochs')
parser.add_argument('--num_iter_G', type=int, default=2, help='number of iterations for training generator')
parser.add_argument('--lrG', type=float, default=0.00005, help='learning rate for generator, default=0.0002')
parser.add_argument('--lrD', type=float, default=0.00005, help='learning rate for discriminator, default=0.0002')
parser.add_argument('--decay', type=float, default=0.9, help='weight decay for RMSProp optimizer')
parser.add_argument('--lambdaA', type=float, default=500, help='lambdaA for L1 loss')
parser.add_argument('--lambdaB', type=float, default=500, help='lambdaB for L1 loss')
params = parser.parse_args()
print(params)

# Directories for loading data and saving results
data_dir = './datasets/' + params.dataset + '/'
save_dir = params.dataset + '_results/'
model_dir = params.dataset + '_model/'

if not os.path.exists(save_dir):
    os.mkdir(save_dir)
if not os.path.exists(model_dir):
    os.mkdir(model_dir)

# Data pre-processing
transform = transforms.Compose([transforms.Resize(params.input_size),
                                transforms.ToTensor(),
                                #transforms.Lambda(lambda x: x.repeat(3,1,1)), #sketch-photo添加这行
                                transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))])

# Train data
train_data_A = DatasetFromFolder(data_dir, subfolder='train/A', transform=transform, fliplr=params.fliplr, is_color=False)
train_data_loader_A = torch.utils.data.DataLoader(dataset=train_data_A,
                                                  batch_size=params.batch_size,
                                                  shuffle=True)
print('aaaaaaaaa',train_data_loader_A)
train_data_B = DatasetFromFolder(data_dir, subfolder='train/B', transform=transform, fliplr=params.fliplr, is_color=False)
train_data_loader_B = torch.utils.data.DataLoader(dataset=train_data_B,
                                                  batch_size=params.batch_size,
                                                  shuffle=True)
print('bbbbbbbbb',train_data_loader_A)
# Test data
test_data_A = DatasetFromFolder(data_dir, subfolder='val/A', transform=transform, is_color=False)
test_data_loader_A = torch.utils.data.DataLoader(dataset=test_data_A,
                                                 batch_size=params.batch_size,
                                                 shuffle=False)
test_data_B = DatasetFromFolder(data_dir, subfolder='val/B', transform=transform, is_color=False)
test_data_loader_B = torch.utils.data.DataLoader(dataset=test_data_B,
                                                 batch_size=params.batch_size,
                                                 shuffle=False)
                                                 
print('tttttttt',test_data_B)
# Get specific test images
test_real_A_data = test_data_A.__getitem__(0).unsqueeze(0)  # Convert to 4d tensor (BxNxHxW)
test_real_B_data = test_data_B.__getitem__(0).unsqueeze(0)
print('zzzzz')
# Models
G_A = Generator(params.num_channel, params.ngf, params.num_channel)
G_B = Generator(params.num_channel, params.ngf, params.num_channel)
D_A = Discriminator(params.num_channel, params.ndf, 1)
D_B = Discriminator(params.num_channel, params.ndf, 1)
G_A.normal_weight_init(mean=0.0, std=0.02)
G_B.normal_weight_init(mean=0.0, std=0.02)
D_A.normal_weight_init(mean=0.0, std=0.02)
D_B.normal_weight_init(mean=0.0, std=0.02)
G_A.cuda()
G_B.cuda()
D_A.cuda()
D_B.cuda()


# Set the logger
D_A_log_dir = save_dir + 'D_A_logs'
D_B_log_dir = save_dir + 'D_B_logs'
if not os.path.exists(D_A_log_dir):
    os.mkdir(D_A_log_dir)
D_A_logger = Logger(D_A_log_dir)
if not os.path.exists(D_B_log_dir):
    os.mkdir(D_B_log_dir)
D_B_logger = Logger(D_B_log_dir)

G_A_log_dir = save_dir + 'G_A_logs'
G_B_log_dir = save_dir + 'G_B_logs'
if not os.path.exists(G_A_log_dir):
    os.mkdir(G_A_log_dir)
G_A_logger = Logger(G_A_log_dir)
if not os.path.exists(G_B_log_dir):
    os.mkdir(G_B_log_dir)
G_B_logger = Logger(G_B_log_dir)

L1_A_log_dir = save_dir + 'L1_A_logs'
L1_B_log_dir = save_dir + 'L1_B_logs'
if not os.path.exists(L1_A_log_dir):
    os.mkdir(L1_A_log_dir)
L1_A_logger = Logger(L1_A_log_dir)
if not os.path.exists(L1_B_log_dir):
    os.mkdir(L1_B_log_dir)
L1_B_logger = Logger(L1_B_log_dir)

img_log_dir = save_dir + 'img_logs'
if not os.path.exists(img_log_dir):
    os.mkdir(img_log_dir)
img_logger = Logger(img_log_dir)


# Loss function
BCE_loss = torch.nn.BCELoss().cuda()
L1_loss = torch.nn.L1Loss().cuda()

# optimizers
G_optimizer = torch.optim.RMSprop(itertools.chain(G_A.parameters(), G_B.parameters()), lr=params.lrG, weight_decay=params.decay)
D_A_optimizer = torch.optim.RMSprop(D_A.parameters(), lr=params.lrD, weight_decay=params.decay)
D_B_optimizer = torch.optim.RMSprop(D_B.parameters(), lr=params.lrD, weight_decay=params.decay)

# Training GAN
D_A_avg_losses = []
D_B_avg_losses = []
G_A_avg_losses = []
G_B_avg_losses = []
L1_A_avg_losses = []
L1_B_avg_losses = []

torch.autograd.set_detect_anomaly(True)

step = 0
D_A_losses = []
D_B_losses = []
G_A_losses = []
G_B_losses = []
L1_A_losses = []
L1_B_losses = []

for epoch in range(params.num_epochs):

    # training
    for i, (real_A, real_B) in enumerate(zip(train_data_loader_A, train_data_loader_B)):
        print('~~~~~~~~~~~~~~')
        # input image data
        real_A = Variable(real_A.cuda())
        real_B = Variable(real_B.cuda())
        for _ in range(params.num_iter_G):
            # Train generator G
            # A -> B
            fake_B = G_A(real_A).detach()
            D_B_fake_decision = D_B(fake_B)
            G_A_loss = BCE_loss(D_B_fake_decision, Variable(torch.ones(D_B_fake_decision.size()).cuda()))

            # forward L1 loss
            recon_A = G_B(fake_B)
            L1_A_loss = L1_loss(recon_A, real_A) * params.lambdaA

            # B -> A
            fake_A = G_B(real_B).detach()
            D_A_fake_decision = D_A(fake_A)
            G_B_loss = BCE_loss(D_A_fake_decision, Variable(torch.ones(D_A_fake_decision.size()).cuda()))

            # backward L1 loss
            recon_B = G_A(fake_A)
            L1_B_loss = L1_loss(recon_B, real_B) * params.lambdaB

            # Back propagation
            G_loss = G_A_loss + G_B_loss + L1_A_loss + L1_B_loss
            print('gggggggggggg',G_loss)
            G_optimizer.zero_grad()
            G_loss.backward(retain_graph=True)            
            G_optimizer.step()

        # Train discriminator D_A
        D_A_real_decision = D_A(real_A)
        D_A_real_loss = BCE_loss(D_A_real_decision, Variable(torch.ones(D_A_real_decision.size()).cuda()))
        print('drrrrrrrr',D_A_real_loss)
        D_A_fake_decision = D_A(fake_A)
        D_A_fake_loss = BCE_loss(D_A_fake_decision, Variable(torch.zeros(D_A_fake_decision.size()).cuda()))
        print('dfffffffff',D_A_fake_loss)

        # Back propagation
        D_A_loss = D_A_real_loss + D_A_fake_loss
        print('+++++++++++',D_A_loss)
        
        with torch.autograd.detect_anomaly(): 
          D_A_optimizer.zero_grad()
          #D_A_loss = D_A_loss.requires_grad_()
          D_A_loss.backward()
          D_A_optimizer.step()
          print('yyyyyyyyyyyyy')

        # Train discriminator D_B
        D_B_real_decision = D_B(real_B)
        D_B_real_loss = BCE_loss(D_B_real_decision, Variable(torch.ones(D_B_real_decision.size()).cuda()))
        D_B_fake_decision = D_B(fake_B)
        D_B_fake_loss = BCE_loss(D_B_fake_decision, Variable(torch.zeros(D_B_fake_decision.size()).cuda()))

        # Back propagation
        D_B_loss = D_B_real_loss + D_B_fake_loss
        D_B_optimizer.zero_grad()
        D_B_loss.backward()
        D_B_optimizer.step()
        

        # loss values
        D_A_losses.append(D_A_loss.item())
        D_B_losses.append(D_B_loss.item())
        G_A_losses.append(G_A_loss.item())
        G_B_losses.append(G_B_loss.item())
        L1_A_losses.append(L1_A_loss.item())
        L1_B_losses.append(L1_B_loss.item())
	
        print('Epoch [%d/%d], Step [%d/%d], D_A_loss: %.4f, D_B_loss: %.4f, G_A_loss: %.4f, G_B_loss: %.4f'
              % (epoch+1, params.num_epochs, i+1, len(train_data_loader_A), D_A_loss.item(), D_B_loss.item(), G_A_loss.item(), G_B_loss.item()))

        # ============ TensorBoard logging ============#
        D_A_logger.scalar_summary('losses', D_A_loss.item(), step + 1)
        D_B_logger.scalar_summary('losses', D_B_loss.item(), step + 1)
        G_A_logger.scalar_summary('losses', G_A_loss.item(), step + 1)
        G_B_logger.scalar_summary('losses', G_B_loss.item(), step + 1)
        L1_A_logger.scalar_summary('losses', L1_A_loss.item(), step + 1)
        L1_B_logger.scalar_summary('losses', L1_B_loss.item(), step + 1)
        step += 1

    D_A_avg_loss = torch.mean(torch.FloatTensor(D_A_losses))
    D_B_avg_loss = torch.mean(torch.FloatTensor(D_B_losses))
    G_A_avg_loss = torch.mean(torch.FloatTensor(G_A_losses))
    G_B_avg_loss = torch.mean(torch.FloatTensor(G_B_losses))
    L1_A_avg_loss = torch.mean(torch.FloatTensor(L1_A_losses))
    L1_B_avg_loss = torch.mean(torch.FloatTensor(L1_B_losses))

    # avg loss values for plot
    D_A_avg_losses.append(D_A_avg_loss)
    D_B_avg_losses.append(D_B_avg_loss)
    G_A_avg_losses.append(G_A_avg_loss)
    G_B_avg_losses.append(G_B_avg_loss)
    L1_A_avg_losses.append(L1_A_avg_loss)
    L1_B_avg_losses.append(L1_B_avg_loss)

    # Show result for test image
    test_real_A = Variable(test_real_A_data.cuda())
    test_fake_B = G_A(test_real_A)
    test_recon_A = G_B(test_fake_B)

    test_real_B = Variable(test_real_B_data.cuda())
    test_fake_A = G_B(test_real_B)
    test_recon_B = G_A(test_fake_A)

    utils.plot_train_result([test_real_A, test_real_B], [test_fake_B, test_fake_A], [test_recon_A, test_recon_B],
                            epoch, save=True, save_dir=save_dir)

    # log the images
    result_AtoB = np.concatenate((utils.to_np(test_real_A), utils.to_np(test_fake_B), utils.to_np(test_recon_A)), axis=3)
    result_BtoA = np.concatenate((utils.to_np(test_real_B), utils.to_np(test_fake_A), utils.to_np(test_recon_B)), axis=3)

    if list(result_AtoB.shape)[1] == 1:
        result_AtoB = result_AtoB.squeeze(axis=1)        # for gray images, convert to BxHxW
    else:
        result_AtoB = result_AtoB.transpose(0, 2, 3, 1)  # for color image, convert to BxHxWxC
    if list(result_BtoA.shape)[1] == 1:
        result_BtoA = result_BtoA.squeeze(axis=1)
    else:
        result_BtoA = result_BtoA.transpose(0, 2, 3, 1)

    info = {
        'result_AtoB': result_AtoB,
        'result_BtoA': result_BtoA
    }

    for tag, images in info.items():
        img_logger.image_summary(tag, images, epoch + 1)


# Plot average losses
avg_losses = []
avg_losses.append(D_A_avg_losses)
avg_losses.append(D_B_avg_losses)
avg_losses.append(G_A_avg_losses)
avg_losses.append(G_B_avg_losses)
avg_losses.append(L1_A_avg_losses)
avg_losses.append(L1_B_avg_losses)
utils.plot_loss(avg_losses, params.num_epochs, save=True, save_dir=save_dir)

# Make gif
utils.make_gif(params.dataset, params.num_epochs, save_dir=save_dir)
# Save trained parameters of model
torch.save(G_A.state_dict(), model_dir + 'generator_A_param.pkl')
torch.save(G_B.state_dict(), model_dir + 'generator_B_param.pkl')
torch.save(D_A.state_dict(), model_dir + 'discriminator_A_param.pkl')
torch.save(D_B.state_dict(), model_dir + 'discriminator_B_param.pkl')
