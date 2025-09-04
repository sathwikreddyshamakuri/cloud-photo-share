import axios, { type AxiosProgressEvent } from "axios";

export async function putToS3(
  putUrl: string,
  file: Blob,
  contentType: string,
  onProgress?: (e: AxiosProgressEvent) => void
) {
  await axios.put(putUrl, file, {
    headers: { "Content-Type": contentType || "application/octet-stream" },
    withCredentials: false, // IMPORTANT for S3 CORS
    onUploadProgress: onProgress, // progress callback (optional)
    // baseURL intentionally omitted (absolute URL)
  });
}
