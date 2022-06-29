# pyright: reportMissingImports=false
import time, os, torch, numpy as np
from upuppi_v0_dataset import UPuppiV0
from torch_geometric.data import DataLoader
from torch import nn
from torch.nn import functional as F
# from models.embedding_model import Net
from models.embedding_GCN import Net
from tqdm import tqdm


# load home directory path from home_path.txt
with open('home_path.txt', 'r') as f:
    home_dir = f.readlines()[0].strip()

BATCHSIZE = 1
start_time = time.time()
print("Training...")
data_train = UPuppiV0(home_dir + 'train/')
data_test = UPuppiV0(home_dir + 'test/')


train_loader = DataLoader(data_train, batch_size=BATCHSIZE, shuffle=True, follow_batch=['x_pfc', 'x_vtx'])
test_loader = DataLoader(data_test, batch_size=BATCHSIZE, shuffle=True, follow_batch=['x_pfc', 'x_vtx'])

model = "contrastive_loss"
model = "embedding_GCN"
model = "embedding_GCN_v1"
model = "embedding_GCN_cheating"
model = "embedding_GCN_cheating_low_lr"
model = "embedding_GCN_nocheating"
model_dir = home_dir + 'models/{}/'.format(model)
#model_dir = '/home/yfeng/UltimatePuppi/deepjet-geometric/models/v0/'

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
device = torch.device('cpu')
# print the device used
print("Using device: ", device, torch.cuda.get_device_name(0))

# create the model
net = Net(pfc_input_dim=13).to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=0.0001)


def contrastive_loss(pfc_enc, vtx_id, num_pfc=64, c=1.0, print_bool=False):
    '''
    Calculate the contrastive loss
    input:
    pfc_enc: the encodding of the inputs
    vtx_id: the true vertex which the particle is connected to
    num_pfc: number of particles to randomly sample
    c: the ratio of positive factor for the particles of same vertex divided by the negative factor
    '''
    # loss which encourages the embedding of same particles to be close and different particles to be far
    # randomly select a set of particles to be used for contrastive loss
    random_perm = torch.randperm(len(pfc_enc))
    if len(pfc_enc) < 2*num_pfc:
        num_pfc = len(pfc_enc)//2
        # print(len(pfc_enc))
    random_indices1 = random_perm[:num_pfc]
    random_indices2 = random_perm[num_pfc:2*num_pfc]
    pfc_enc_1 = pfc_enc[random_indices1, :]
    pfc_enc_2 = pfc_enc[random_indices2, :]
    vtx_id_1 = vtx_id[random_indices1]
    vtx_id_2 = vtx_id[random_indices2]
    # get a mask which is c if the particles are the same and -1 if they are different
    mask = -1+(c+1)*(vtx_id_1 == vtx_id_2).float()
    euclidean_dist = F.pairwise_distance(pfc_enc_1, pfc_enc_2)
    loss = torch.mean(mask*torch.pow(euclidean_dist, 2))
    if print_bool:
        print("Contrastive loss: {}, loss from particles: {}".format(loss, torch.mean(mask*torch.pow(euclidean_dist, 2))))
    return loss

def contrastive_loss_v2(pfc_enc, vtx_id, c1=0.5, c2=1, print_bool=False):
    unique_vtx = torch.unique(vtx_id)
    if len(unique_vtx) == 1:
        # if there is only one vertex, return 0 and corresponding gradient
        # print warning if there is only one vertex
        print("Warning: there is only one vertex")
        return 0
    mean_vtx = torch.zeros((len(unique_vtx), pfc_enc.shape[1])).to(device)
    for i, vtx in enumerate(unique_vtx):
        mean_vtx[i] = torch.mean(pfc_enc[vtx_id == vtx, :], dim=0)
    # get the mean of the particles of the different vertex
    mean_vtx_diff = torch.zeros((len(unique_vtx), pfc_enc.shape[1])).to(device)
    for i, vtx in enumerate(unique_vtx):
        mean_vtx_diff[i] = torch.mean(pfc_enc[vtx_id != vtx, :], dim=0)
    # get the distance between the mean of the particles of the same vertex and the mean of the particles of the different vertex
    euclidean_dist_vtx = F.pairwise_distance(mean_vtx, mean_vtx_diff)
    loss = -c2*torch.mean(torch.pow(euclidean_dist_vtx, 2))
    # add variance of the particles of the same vertex
    var_vtx = torch.zeros((len(unique_vtx), pfc_enc.shape[1])).to(device)
    for i, vtx in enumerate(unique_vtx):
        if len(pfc_enc[vtx_id == vtx, :]) > 1:
            var_vtx[i] = torch.var(pfc_enc[vtx_id == vtx, :], dim=0)
        else:
            var_vtx[i] = 0
        # var_vtx[i] = torch.var(pfc_enc[vtx_id == vtx, :], dim=0) + 1e-6
        # if any of the variance is nan, set it to 0
        # if torch.isnan(var_vtx[i]).any():
        #     print(i)
        #     print("vtx_id: {}".format(vtx_id))
        #     print("var_vtx: {}".format(var_vtx[i]))
        #     var_vtx[i][torch.isnan(var_vtx[i])] = 0
        #     print("Warning: variance is nan")
    loss += c1*torch.mean(torch.pow(var_vtx, 2))
    # print all the losses, the loss from the different means and the loss from the variance
    if print_bool:
        print("Contrastive loss: {}, loss from vtx distance: {}, loss from variance: {}".format(loss, -c2*torch.mean(torch.pow(euclidean_dist_vtx, 2)), c1*torch.mean(torch.pow(var_vtx, 2))))
        # if any of the loss is nan, print the data
    if torch.isnan(loss):
        print("Contrastive loss is nan")
        print("pfc_enc: {}".format(pfc_enc))
        print("vtx_id: {}".format(vtx_id))
        print("mean_vtx: {}".format(mean_vtx))
        print("mean_vtx_diff: {}".format(mean_vtx_diff))
        print("euclidean_dist_vtx: {}".format(euclidean_dist_vtx))
        print("var_vtx: {}".format(var_vtx))
        raise(ValueError)
        # return 0 loss and gradient
        return 0
    return loss
        


def process_batch(data):
    '''
    Process the batch of data
    input:
    data: the data batch
    output:
    data: the processed data batch
    '''
    return data
    # get the data
    x_pfc = data.x_pfc.to(device)
    # normalize z to [-1, 1]
    data.x_pfc[:,12] = data.x_pfc[:,12]/200.0
    # zero out z
    data.x_pfc[:,12] = data.x_pfc[:,12]*0.0
    # normalize the true z to [-1, 1]
    data.y = data.y/200.0
    # return the data
    return data



def train(reg_ratio = 0.01, neutral_weight = 1):
    net.train()
    loss_fn = contrastive_loss_v2
    train_loss = 0
    for counter, data in enumerate(tqdm(train_loader)):
        data = data.to(device)
        # data = process_batch(data)
        optimizer.zero_grad()
        # vtx_id = (data.truth != 0).int()
        vtx_id = data.truth.int()
        # adding in the true vertex id itself to check if model is working
        input_data = torch.cat((data.x_pfc[:,:-1], vtx_id.unsqueeze(1)), dim=1)
        charged_idx, neutral_idx = torch.nonzero(data.x_pfc[:,11] != 0).squeeze(), torch.nonzero(data.x_pfc[:,11] == 0).squeeze()
        # replace the vertex id of the neutral particles with 0.5
        # vtx_id[neutral_idx] = 0.5
        # input_data[neutral_idx, -1] = 0.5
        # input_data = data.x_pfc
        pfc_enc = net(input_data)
        # print(net.state_dict())
        # if pfc enc is nan, print the data
        if torch.isnan(pfc_enc).any():
            print(old_state_dict)
            print("pfc_enc is nan")
            print("pfc_enc: {}".format(pfc_enc))
            print("input_data: {}".format(input_data))
            print("charged_idx: {}".format(charged_idx))
            print("neutral_idx: {}".format(neutral_idx))
            print("data.x_pfc: {}".format(data.x_pfc))
            print("data.truth: {}".format(data.truth))
            # print model parameters
            print("net.state_dict(): {}".format(net.state_dict()))
            print("net.named_parameters(): {}".format(net.named_parameters()))
            raise(ValueError("pfc_enc is nan"))
        old_state_dict = net.state_dict()
        if neutral_weight != 1:  
            charged_embeddings, neutral_embeddings = pfc_enc[charged_idx], pfc_enc[neutral_idx]
            charged_loss, neutral_loss = loss_fn(charged_embeddings, vtx_id[charged_idx], print_bool=False), loss_fn(neutral_embeddings, vtx_id[neutral_idx], print_bool=False)
            loss = (charged_loss + neutral_weight*neutral_loss)/(1+neutral_weight)
            loss += loss_fn(pfc_enc, vtx_id, c1=0.1, print_bool=False)
        else:
            loss = loss_fn(pfc_enc, vtx_id, c1=0.1, print_bool=False)
        loss += reg_ratio*((torch.norm(pfc_enc, p=2, dim=1))**4).mean()
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
        if counter % 5000 == 1:
            print("Counter: {}, Average Loss: {}".format(counter, train_loss/counter))
            print("Regularization loss: {}".format(((torch.norm(pfc_enc, p=2, dim=1))**4).mean()))
            if neutral_weight != 1:
                print("Charged loss: {}, Neutral loss: {}".format(charged_loss, neutral_loss))
                print("number of charged particles: {}, number of neutral particles: {}".format(len(charged_idx), len(neutral_idx)))
            # loss = contrastive_loss(pfc_enc, vtx_id, num_pfc=64, c=0.1, print_bool=True)
            loss = loss_fn(pfc_enc, vtx_id, c1=0.1, print_bool=True)
    train_loss = train_loss/counter
    return train_loss

# test function
@torch.no_grad()
def test():
    net.eval()
    test_loss = 0
    for counter, data in enumerate(tqdm(train_loader)):
        data = data.to(device)
        pfc_enc = net(data.x_pfc)
        vtx_id = data.truth
        loss = contrastive_loss_v2(pfc_enc, vtx_id)
        test_loss += loss.item()
    test_loss = test_loss / counter
    return test_loss

# train the model
if __name__ == "__main__":
    for epoch in range(20):
        loss = 0
        test_loss = 0
        loss = train(reg_ratio = 0.01, neutral_weight = epoch+1)
        state_dicts = {'model':net.state_dict(),
                    'opt':optimizer.state_dict()} 
        torch.save(state_dicts, os.path.join(model_dir, 'epoch-{}.pt'.format(epoch)))
        print("Model saved at path: {}".format(os.path.join(model_dir, 'epoch-{}.pt'.format(epoch))))
        print("Time elapsed: ", time.time() - start_time)
        print("-----------------------------------------------------")
        test_loss = test()
        print("Epoch: ", epoch, " Loss: ", loss, " Test Loss: ", test_loss)
