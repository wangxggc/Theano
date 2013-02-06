import numpy

import theano
import theano.tensor as T
from theano.gof import local_optimizer
from theano.sandbox.cuda.basic_ops import as_cuda_ndarray_variable, host_from_gpu, HostFromGpu
from theano.misc import strutil
from theano.tensor.nnet.Conv3D import Conv3D
from theano.sandbox.cuda.opt import register_opt
from theano.sandbox.cuda import CudaNdarrayType, GpuOp

class GpuConv3D(GpuOp):
    """ GPU implementation of Conv3D """

    def __eq__(self, other):
        return type(self) == type(other)

    def __hash__(self):
        return hash(type(self))

    def __str__(self):
        return '%s' % (self.__class__.__name__)

    def make_node(self, V, W, b, d):
        """
            :param V: Visible unit, input
            :param W: Weights, filter
            :param b: bias
            :param d: strides when moving the filter over the input
        """
        V_ = as_cuda_ndarray_variable(V)
        W_ = as_cuda_ndarray_variable(W)
        b_ = as_cuda_ndarray_variable(b)
        d_ = T.as_tensor_variable(d)

        return theano.Apply(self, inputs=[V_, W_, b_, d_],
                            outputs = [ CudaNdarrayType(dtype=V_.dtype, broadcastable=(V_.broadcastable[0],W_.broadcastable[0],False,False,False))() ] )

    def c_code_cache_version(self):
        return ()
    def c_code(self, node, nodename, inputs, outputs, sub):
        V, W, b, d = inputs
        fail = sub['fail']

        H = outputs[0]

        codeSource =  """
                        ///////////// < code generated by GpuConv3D >

                        //printf("\t\t\t\tConv3DGPU c code\\n");

                        //Check dimensionality of inputs
                        if (%(W)s->nd != 5)
                        {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: W must be a 5 dimensional CudaNdarray");
                            %(fail)s
                        }

                        if (%(V)s->nd != 5)
                        {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: V must be a 5 dimensional CudaNdarray");
                            %(fail)s
                        }

                        if (%(b)s->nd != 1)
                        {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: b must be a vector CudaNdarray");
                            %(fail)s
                        }

                        if (%(d)s->nd != 1)
                        {
PyErr_Format(PyExc_ValueError, "GpuConv3D: d must be a vector CudaNdarray");
                            %(fail)s

                        }
                        if (%(d)s->dimensions[0] != 3)
                        {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: 3 stride length arguments expected (row, col, time) but %%li were given", %(d)s->dimensions[0]);
                            %(fail)s

                        }

{ //extra scope so fail doesn't jump over declarations
                        //Read and check sizes of inputs
                        const int batchSize = CudaNdarray_HOST_DIMS(%(V)s)[0];
                        const int outputChannels =  CudaNdarray_HOST_DIMS(%(W)s)[0];
                        const int inputChannels = CudaNdarray_HOST_DIMS(%(V)s)[4];
                        if (CudaNdarray_HOST_DIMS(%(W)s)[4] != inputChannels)
                        {
                            PyErr_Format(PyExc_ValueError, "GpuConv3D: W operates on a %%i channel image but the image has %%i channels",CudaNdarray_HOST_DIMS(%(W)s)[4],inputChannels);
                            %(fail)s
                        }
{  //extra scope so error handler jumps don't cause errors
                        const int filterHeight = CudaNdarray_HOST_DIMS(%(W)s)[1];
                        const int filterWidth = CudaNdarray_HOST_DIMS(%(W)s)[2];
                        const int filterDur = CudaNdarray_HOST_DIMS(%(W)s)[3];
                        const int vidHeight = CudaNdarray_HOST_DIMS(%(V)s)[1];
                        const int vidWidth = CudaNdarray_HOST_DIMS(%(V)s)[2];
                        const int vidDur = CudaNdarray_HOST_DIMS(%(V)s)[3];
            if (vidHeight < filterHeight)
            {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: W has a height of %%i but V is only %%i pixels tall",filterHeight,vidHeight);
                %(fail)s
            }
{ // extra scope so fail works
            if (vidWidth < filterWidth)
            {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: W has a width of %%i but V is only %%i pixels wide",filterWidth,vidWidth);
                %(fail)s
            }
{ // extra scope so fail works
            if (vidDur < filterDur)
            {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: W has a duration of %%i but V is only %%i pixels long",filterDur,vidDur);
                %(fail)s
            }
{ // extra scope so fail works

                        //Read and check stride arguments
                        const int dr = *(dtype_%(d)s*)PyArray_GETPTR1(%(d)s,0);
                        const int dc = *(dtype_%(d)s*)PyArray_GETPTR1(%(d)s,1);
                        const int dt = *(dtype_%(d)s*)PyArray_GETPTR1(%(d)s,2);
                        if (dr <= 0 || dc <= 0 || dt <= 0)
                        {
                PyErr_Format(PyExc_ValueError, "GpuConv3D: Strides must all be positive but are %%i, %%i, %%i", dr, dc, dt);
                %(fail)s
                        }
{ // extra scope so fail works

                        //Make correctly sized output
                        const int outputHeight = int( (vidHeight - filterHeight) / dr )+1;
                        const int outputWidth = int( (vidWidth - filterWidth) / dc )+1;
                        const int outputDur = int( (vidDur - filterDur) / dt ) +1;

                        npy_intp dims[5];
                        dims[0] = batchSize;
                        dims[4] = outputChannels;
                        dims[1] = outputHeight;
                        dims[2] = outputWidth;
                        dims[3] = outputDur;

                        if(!(%(H)s) || CudaNdarray_HOST_DIMS(%(H)s)[0]!=dims[0] ||
                        CudaNdarray_HOST_DIMS(%(H)s)[1]!=dims[1] ||
                        CudaNdarray_HOST_DIMS(%(H)s)[2]!=dims[2] ||
                        CudaNdarray_HOST_DIMS(%(H)s)[3]!=dims[3] ||
                        CudaNdarray_HOST_DIMS(%(H)s)[4]!=dims[4]){
                                Py_XDECREF(%(H)s);
                                %(H)s = (CudaNdarray*)CudaNdarray_NewDims(5,dims);
                                if (!(%(H)s)) {

                    PyErr_Format(PyExc_MemoryError, "GpuConv3D: could not allocate output");
                            %(fail)s
                                }
                        }
{ // extra scope so fail will not cross declarations
                        //#define ELEM_AT(x, i) * ( dtype_ ## x *) ( x->data + (i) )####################

                        const int ws4 = CudaNdarray_HOST_STRIDES(%(W)s)[4];
                        const int vs4 = CudaNdarray_HOST_STRIDES(%(V)s)[4];
                        const int ws3 = CudaNdarray_HOST_STRIDES(%(W)s)[3];
                        const int vs3 = CudaNdarray_HOST_STRIDES(%(V)s)[3];
                        const int ws2 = CudaNdarray_HOST_STRIDES(%(W)s)[2];
                        const int vs2 = CudaNdarray_HOST_STRIDES(%(V)s)[2];
                        const int ws1 = CudaNdarray_HOST_STRIDES(%(W)s)[1];
                        const int vs1 = CudaNdarray_HOST_STRIDES(%(V)s)[1];
                        const int ws0 = CudaNdarray_HOST_STRIDES(%(W)s)[0];
                        const int vs0 = CudaNdarray_HOST_STRIDES(%(V)s)[0];

                        // Compute H
                        //H[i,x,y,t,j] = b_j + sum_k sum_l sum_m sum_z W[j,k,l,m,z] V[i, dr*r+k,dc*c+l,dt*t+m,z]

bool out_contiguous = CudaNdarray_is_c_contiguous(%(H)s);
int version = -1;
int verbose = 0;
bool subsample =(dr>1)||(dc>1)||(dt>1);
bool b_strided = (CudaNdarray_HOST_STRIDES(%(b)s)[0]!=1) && !(CudaNdarray_HOST_STRIDES(%(b)s)[0]==0 && outputChannels==1);
bool work_complete = false;

if(out_contiguous && !b_strided && (version==0||version==-1) && outputDur<=512 && !work_complete){
    //conv_rows_stack
    dim3 grid(outputHeight*outputWidth,batchSize*outputChannels);
    dim3 threads(outputDur);

    int shared_size=0;
        conv_rows_stack<<<grid, threads, shared_size>>>(
        CudaNdarray_DEV_DATA(%(V)s), CudaNdarray_DEV_DATA(%(W)s), CudaNdarray_DEV_DATA(%(b)s), CudaNdarray_DEV_DATA(%(H)s),
        vidHeight, vidWidth, vidDur,
        filterHeight, filterWidth, filterDur,
        outputChannels, inputChannels,
        dr,dc,dt,
        vs3,vs2,vs1,vs4,vs0,
        ws3,ws2,ws1,ws4,ws0);

        CNDA_THREAD_SYNC;
        cudaError_t sts = cudaGetLastError();
        if (cudaSuccess == sts)
        {
            work_complete = true;
            if (verbose>1) printf("threads.x=%%i, threads.y=%%i, grid.x=%%i, grid.y=%%i, shared_size=%%i, nb_threads=%%i\\n", threads.x, threads.y, grid.x, grid.y, shared_size, threads.x * threads.y);
            if (verbose) printf("INFO: used 'conv_rows_stack' version\\n");
        }
        else
        {
            if (verbose) printf("threads.x=%%i, threads.y=%%i, grid.x=%%i, grid.y=%%i, shared_size=%%i, nb_threads=%%i\\n", threads.x, threads.y, grid.x, grid.y, shared_size, threads.x * threads.y);
            if (verbose) printf("ERROR: all implementations failed for GpuConv3D! (%%s)",cudaGetErrorString(sts));
            PyErr_Format(PyExc_RuntimeError, "ERROR: all implementations failed for GpuConv3D! (%%s)",
                    cudaGetErrorString(sts));
            %(fail)s
        }


}

if(!work_complete){
            PyErr_Format(PyExc_RuntimeError, "ERROR: no implementations executed for this GpuConv3D!");
            %(fail)s
}

}}}}}}} //extra scope so error handler jumps don't cross declarations
                        ///////////// < /code generated by GpuConv3D >
        """
        return strutil.render_string(codeSource,locals())

    def c_support_code_apply(self, node, nodename):
        # This code is not sensitive to the ignore_border flag.
        # It runs for every position in the output z, and then computes the gradient for the
        # input pixels that were downsampled to that z-position.
        codeSource =  """
__global__ void
//thread block size = out_dur
//grid block size =(out_len*out_wid, nb kern *nb batch)
//
conv_rows_stack( float* img, float* kern, float* bias, float* out,
                 int img_len, int img_wid, int img_dur,
                 int kern_height, int kern_wid, int kern_dur,
                 int nkern, int input_channels,
                 int dr, int dc, int dt,
                 int img_stride_frame, int img_stride_col, int img_stride_row,
                 int img_stride_ochannel, int img_stride_batch,
                 int kern_stride_frame, int kern_stride_col, int kern_stride_row,
                 int kern_stride_stack, int kern_stride_okern)
{
  int __shared__ out_len, out_wid, out_dur, batch_id, kern_id;
  float  __shared__ *d_img, *d_kern;
  out_len = int( (img_len - kern_height) / dr )+1;
  out_wid = int( (img_wid - kern_wid) / dc )+1;
  out_dur = int( (img_dur - kern_dur) / dt )+1;

  batch_id= blockIdx.y/nkern;
  kern_id = blockIdx.y - batch_id*nkern;

  const int out_row = blockIdx.x%out_len;
  const int out_col = blockIdx.x/out_len;
  const int out_frame=threadIdx.x;

  img += batch_id*img_stride_batch + out_row*dr*img_stride_row + out_col*dc*img_stride_col+out_frame*dt*img_stride_frame;
  kern += kern_id*kern_stride_okern;
    float sum = 0.0f;
    for (int z = 0; z < input_channels; z++) {//1 for first layer
        for (int k =0; k < kern_height; k++) {
          for (int l = 0; l < kern_wid; l++) {
            for (int m = 0; m < kern_dur; m++) {
              sum += img[img_stride_ochannel*z+img_stride_row*k+img_stride_col*l+img_stride_frame*m] *
                         kern[kern_stride_stack*z+kern_stride_row*k+kern_stride_col*l+kern_stride_frame*m];
            }
          }
        }

      out[batch_id*nkern*out_len*out_wid*out_dur+//the good batch
          out_frame*nkern+//the output frame
          out_row*out_wid*out_dur*nkern+//the output row
          out_col*out_dur*nkern + //the output_col
          kern_id //the output image (channel)
] = sum + bias[kern_id];
    }
}


            """

        return codeSource

gpu_convd = GpuConv3D()

@register_opt()
@local_optimizer([])
def local_gpu_conv3d(node):
    if isinstance(node.op, Conv3D):
        if numpy.any([i.owner and isinstance(i.owner.op, HostFromGpu) for i in node.inputs]):
            if numpy.all([o.type.dtype == 'float32' for o in node.outputs]):
                V, W, b, d = node.inputs
                return [host_from_gpu(gpu_convd(as_cuda_ndarray_variable(V),as_cuda_ndarray_variable(W), as_cuda_ndarray_variable(b), d))]
