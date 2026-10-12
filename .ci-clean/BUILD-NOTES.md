# Clean native CPU dependency experiment — NOT RELEASE CLEARED

Public Decord2 source: https://github.com/johnnynunez/decord2/tree/1b4cfbd5d2964d411341ccf252051e516845430e (3.4.0).
DLPack: https://github.com/dmlc/dlpack/tree/5c792cef3aee54ad8b7000111c9dc1797f327b59.
DMLC: https://github.com/dmlc/dmlc-core/tree/d07fb7a443b5db8a89d65a15a024af6a425615a5.
FFmpeg: https://ffmpeg.org/releases/ffmpeg-8.1.1.tar.xz, SHA256 b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3, UNPATCHED.

The build recipe is the accompanying clean-native.yml; FFmpeg's generated config is included. Decord's existing local-version hook labels the changed payload 3.4.0+cleanlgpl.1. Python and C++ implementation source are unchanged. The installed runtime __version__ remains upstream's source version; distribution metadata carries the local suffix.

## API trace and configuration decision

At the exact Decord pin, VideoReader/VideoLoader and AudioReader/AVReader are decode APIs, not encoding APIs. video_reader.cc:74-77 and audio_reader.cc:101-103 call avformat_open_input, including custom byte-buffer IO. video_reader.cc:103 and audio_reader.cc:141 select avcodec_find_decoder. The threaded decoder sends packets and receives frames. A complete scan of src/ for avcodec_find_encoder, avcodec_send_frame, avcodec_receive_packet, avformat_alloc_output_context, av_write_frame, av_interleaved_write_frame, x264 and x265 found no matches. There is no public Python video writer. Removing external x264/x265 encoders does not remove the traced decode API: native FFmpeg H.264/HEVC decoders are retained. This is NOT a claim that every input codec/network behavior matches the vendor graph.

The decoder generates scale and transpose filters (threaded_decoder.cc:17-38) and format=rgb24 (filter_graph.cc:78-90), with buffer/buffersink at lines 27-28. All available LGPL built-in filters are retained. All available built-in demuxers, parsers and decoders are retained; encoders, muxers, device backends and hardware accelerators are disabled. Network support stays enabled; Windows SChannel is explicitly enabled for TLS. The vendor's external codec implementations (including dav1d, libvpx, opus, opencore-amr, libwebp), external compression/character-conversion libraries and GPL components are not enabled. Disabling external autodetection can remove formats such as compressed image codecs or alternative AV1 implementations. Runtime-generated exact compiled manifests, not this qualitative description, are authoritative. Assembly disabled: no optimization/performance parity claim. No CUDA/NVDEC/NVENC/GPU claim.

## Licensing / distribution boundary

The stock GPL classification is unchanged. --disable-gpl --disable-version3 --disable-nonfree, together with no external libraries, selects the stock LGPL-2.1-or-later profile. All stock FFmpeg COPYING texts (including GPL texts) and LICENSE.md are retained, not stripped or relabelled. Decord/DLPack/DMLC original notices are staged separately. Microsoft's compiler/SDK/runtime are not relicensed by these open-source notices.

No Microsoft CRT DLL is copied into this wheel. The native build uses the dynamic Microsoft CRT and treats its public redistributable as an external prerequisite. A runner's installed System32 DLL and successful execution do NOT establish correspondence/compatibility with a particular public redistributable installer. The parallel CRT origin audit must supply that exact installer/compatibility witness. Pending that, redistribution remains BLOCKED. Source/relinking instructions and notices here are experimental, pending full per-object/header attribution and distribution review; this is not legal clearance.

No binary artifact is uploaded by this workflow: reports only. The original vendor wheel and original worktree remain unchanged. No PR or package publication.
